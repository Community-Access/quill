# Quill Radio 3.0: The Long Version

This is the companion to the Quill Radio 3.0 release notes. Those tell the
story; this one tells the reasoning.

Nothing here is required reading. It exists because the reasoning behind a
decision is worth as much as the decision, because several things in 3.0 were
built the second-obvious way for a first-obvious reason that turned out to be
wrong, and because "we fixed some bugs" is not a sentence this project wants to
write.

It is organised by subject rather than by importance. Read the section you are
curious about and ignore the rest.

---

## 1. Described audio, and the fight to reach it on YouTube

The detection is deliberately generous, because publishers label these tracks
half a dozen ways -- "English (Audio Description)", "descriptive", "eng-desc",
"English AD" -- and all of them mean the same thing to somebody who needs one.

**And on YouTube, finding these tracks took a fight that is worth telling.**

Most described content there is a separate upload with the narration mixed in
-- Apple's and Microsoft's accessibility films both work that way, and they
play perfectly, because the description simply *is* the audio. But some videos
publish a real selectable descriptive track: Emily Graslie's *ART LAB* series,
several of Adam Savage's *Tested* builds, two Apple films.

Ask YouTube for those the ordinary way and it names the renditions -- *"English
original"*, *"English descriptive"* -- then hands over only the original,
keeping the described track's address for its own player.

Quill Radio now asks a second way at the same time, as YouTube's own iOS
player, which is given every rendition with a playable address. So the
described track is *there*, named, first in the list, one keystroke away -- on
a platform where the player in your browser makes you find a settings gear
inside a submenu to learn it exists at all.

The same door opened every dubbed track, which is why a multi-language video
now lists all of its renditions by name rather than by code.

---

## 2. YouTube as a station

### 2.1 Why the helper is bundled rather than fetched

The `yt-dlp` helper that finds the audio behind a link is built into Quill
Radio, so your first YouTube link simply plays -- no download, no consent
prompt, nothing to agree to before you have heard anything. It costs about 3 MB
in the installer, which is a better trade than a dialog standing between you
and the thing you asked for.

The helper is bundled only in the apps that can actually use it -- Quill Radio,
Audio Studio and Audio Converter -- so Weather, Cast, Social, Beacon and
Inkwell do not carry it.

### 2.2 Update YouTube Support, and the trade it manages

**Station > Update YouTube Support...** fetches a newer `yt-dlp` than the one
your copy was built with. An update installed this way takes precedence over
the built-in copy from then on. It tells you which version you ended up with,
asks before it reaches the network, and is off in Safe Mode.

It exists because of a deliberate architectural choice. Quill Radio does not
use YouTube's official Data API, which would require every listener to create a
Google Cloud project and paste an API key in before searching. It uses yt-dlp's
keyless extraction -- the same approach FreeTube, NewPipe and Invidious all
take. The trade-off is that YouTube occasionally changes how its site works and
extraction breaks until upstream fixes it. This command is how you get the fix
without waiting for the next Quill Radio release.

### 2.3 What one request buys

Finding the audio behind a link takes one request, and that request answers
with far more than an audio address. Quill Radio keeps all of it: the video's
length, its uploader, its description, the chapters the uploader published, and
whether a caption track exists. None of it costs an extra moment or an extra
connection -- it rides the request the app was making anyway.

A live broadcast reports no length at all, which is the honest answer: it has
no timeline to sit on.

### 2.4 The seek that invented its own numbers

Rewind / Forward 30 Seconds always ran the *live-stream* seek, which moves
inside mpv's rolling buffer and reports how far behind the live edge you now
are. On a finished video there is no live edge, so that number was invented --
exactly the kind of confident wrong measurement this app refuses to make
anywhere else.

The keys now pick the operation the source actually deserves: a video moves
along its own timeline and says "3 minutes 10 seconds of 18 minutes 40
seconds"; a live stream behaves precisely as before.

### 2.5 Adding a playlist is an import, and the words matter

Adding a playlist is an **import**, not a subscription and not a play queue.
The videos you pick become ordinary favorites and sit alongside everything else
rather than in a folder of their own. Nothing plays through them in order.
Nothing re-checks the playlist later, so videos added upstream after your
import are not picked up -- run the command again on the same link to collect
them, and anything already in your favorites is skipped rather than duplicated.

Playing a playlist as a queue, and keeping one in step with its source, are
separate pieces of work. Saying so is better than letting "playlist support"
imply either.

The listing itself is deliberately shallow: one request for the whole playlist
rather than one per video, and no video's audio is fetched until you play it.
Rows read as whole sentences -- "3. Introducing layers, 5 minutes 31 seconds,
3Blue1Brown" -- so there are no columns to arrow across, and times are spelled
out in words on purpose, because "5:31" read aloud is ambiguous unless you
already know it is a time.

A *watch* link that happens to carry a `list=` in it is still just that one
video. You asked for the video; quietly turning it into fifty stations would be
a nasty surprise.

### 2.6 Why a file, and not a "Sign in with Google" button

**Import YouTube Subscriptions...** reads the `subscriptions.csv` from your own
Google export. This came from a listener asking whether Quill Radio could sign
in with their YouTube account and synchronise their history, and the honest
answers are worth stating.

Signing in would mean attaching your real Google account to an app that also
extracts audio from YouTube pages -- something YouTube does not endorse -- so it
is the *account*, not just the feature, that would be at risk. It would also
require you to create your own Google Cloud project first: seven steps of
developer console before you hear a single channel.

Reading a file you exported yourself avoids all of it. Nothing authenticates,
no password or token is stored, no request is made to Google at all, and it
works offline and in Safe Mode.

**On Premium and history, plainly.** Quill Radio cannot sign you in to YouTube
Premium, and Premium's benefits do not carry into it. YouTube's developer terms
specifically forbid a third-party app from separating audio from video -- which
is what audio-only playback *is* -- from playing in a background player, and
from storing anything for offline use. There is no Premium exception to ask
for. Watch history cannot be synchronised either, by us or by anyone: YouTube
removed watch history and Watch Later from outside reach years ago, and answers
the request with "Watch history data cannot be retrieved through the API."

It is a one-time import, deliberately: nothing keeps syncing, nothing runs in
the background, and re-importing later skips what you already follow.

---

## 3. Podcasts

### 3.1 The empty-chart bug you may have hit

Apple tags a charting show with its *leaf* genre and never with the genres
above it -- a show filed under Books carries Books and not Arts. Filtering a
storefront's top hundred by Arts therefore returned nothing at all, which looks
exactly like an empty chart.

Choosing a genre now includes everything beneath it, so Arts means Arts *and*
Books, Design, Food and the rest.

### 3.2 It is gentle with Apple, deliberately

One chart request serves every genre in a storefront rather than one per genre.
The genre tree is kept for a week, charts for six hours, and a resolved feed
address for a month. Wandering the tree costs almost nothing after the first
visit, and nobody's directory is hammered for the privilege.

### 3.3 Where the line between Radio and Cast falls

How many episodes each show lists is one preference (25 newest by default) --
deliberately the only podcast setting Quill Radio has, because the rich side of
podcasting belongs to QUILL Cast.

The handoff runs both ways without either app writing the other's files. Play a
subscribed show's episode in Quill Radio -- half of it over lunch, or all of it
-- and QUILL Cast learns about it at its next launch: the episode stops
presenting as brand new in the Inbox, and Continue Listening knows your real
place. A small handoff record carries the news, so nothing can be lost
whichever app is open.

---

## 4. The station catalog

### 4.1 What is offline, and what is not

The catalog covers the station directory itself: Radio Browser's 62,000+
stations and every axis through them, SomaFM, and the Project Gutenberg
audiobook shelf. These branches answer with no internet at all.

The rest stays live, each for a stated reason:

- **Apple Podcasts (iTunes)** -- charts are rankings, and Apple's terms bar
  storing them.
- **TuneIn** -- its directory is a remote tree that may not be stored.
- **iHeart** -- its terms do not allow storing its listings.
- **Internet Archive** -- its collections run to half a million items; a copy
  would dwarf the app.
- **LibriVox** -- live *for now*: its full chapter listing alone is bigger than
  everything else in the catalog combined, and it deserves a compact format of
  its own rather than a squeezed-in copy.
- **The music charts (Audius, Mixcloud, ccMixter)** -- charts are stale the
  moment they are stored.

### 4.2 How an outage is told apart from the truth

A station that disappears is hidden at once but only truly forgotten after two
weeks, so one bad afternoon at a directory cannot hollow out your catalog. A
source that answers with nothing when it had thousands yesterday is treated as
an outage, not as the truth.

Rankings are statements about *now*, so Popular and Trending stay live-first.
When the directory cannot answer, the catalog steps in with its vote snapshot
-- and every one of those rows says "as of 2 hours ago" out loud, because an
unlabeled stale ranking is a small lie and a labeled one is a rescue.

### 4.3 The fine print that is actually good news

- The whole catalog adds about seven and a half megabytes to the download.
- Turning the catalog off restores live-only browsing exactly: nothing stored,
  no background requests of any kind.
- Safe Mode never refreshes; reading the local catalog is allowed, because it
  is local data, exactly like your favorites.
- A branch you hide in Choose Browse Sources is not refreshed either. Off means
  off -- not in the tree, never contacted.
- Rebuild the catalog from scratch and your stations are byte-for-byte
  untouched, and there is a test that proves exactly that.

---

## 5. The browse tree, source by source

### 5.1 Internet Archive: honesty about depth

The depth is not something we built -- the Archive genuinely is a tree, every
item declares its parents, and one query shape walks the whole thing.

A folder that holds more than a page says **More...** and tells you how much it
is hiding, because a tree that quietly shows the first hundred of eight
thousand is lying. And an item with no published rights information says
exactly that, rather than letting you assume.

### 5.2 LibriVox: why there is deliberately no "By Title"

LibriVox's own catalogue can be browsed by author, by genre and by date, and
not by title -- there is simply no such list to ask it for. Offering the branch
anyway would give you a folder that always came back empty, and a branch that
quietly finds nothing is worse than one that is not there.

### 5.3 Project Gutenberg: paging rather than truncating

Every topic and language pages through its whole shelf with a "More
audiobooks" row. A list that stops at the first thirty-two and says nothing
would read as the whole answer, which is the kind of quiet lie this app does
not tell.

### 5.4 The three music libraries, and what each one is

**Audius** -- independent music, trending overall and within 27 genres. No key;
the app identifies itself by name. Gated tracks are dropped rather than listed
and then refused when you press Enter.

**Mixcloud** -- 28 music and 10 talk categories of DJ sets and radio shows.
Browsing is metadata only: Quill Radio never extracts a Mixcloud stream, and
activating a show opens it on Mixcloud in your own browser. **The row says so
before you press Enter**, not after.

**ccMixter** -- Creative Commons music by tag, every row carrying its licence in
the row itself. For material offered under terms, showing the terms is the whole
courtesy. And the rows *play*: ccMixter's file host refuses any player that does
not arrive with a Referer from ccmixter.org -- measured, not guessed -- so Quill
Radio sends exactly that header for ccMixter and nothing else, in playback and
in Record Now alike.

### 5.5 AudioPub: two honest boundaries

Nothing from AudioPub is stored on your computer. The platform is open source,
but the *audio* belongs to the people who uploaded it, and Station Catalog
Status says exactly that.

And Discover is deliberately the only branch for now. Newest, popular, search
and live broadcasts all exist on AudioPub's side, and rather than scrape its
internals, we are asking its developer to bless a small public API. When that
lands, so do the branches.

### 5.6 Explore, and the two axes that were removed

**Opening a place gives you the place, not a sample of it.** By City used to
take Wikidata's list of stations for a city and look each one up, which sounds
right and is backwards: that list is a capped, unordered slice of tens of
thousands of stations, so Arizona could open to nothing at all while KJZZ, KBAQ
and forty-seven others sat there playable. A place is now asked of Radio Browser
directly -- the set that can actually play -- and Wikidata's call signs top it
up. **By Format** works the same way, against Radio Browser's tags.

**Two axes have been removed, and the rule they leave behind is a good one: an
axis stays only if the station directory can answer it.**

**By Network** went first. Wikidata's "original broadcaster" is recorded for two
US radio stations, so the folder could never have listed anything.

**By Owner** went next, and it is the more interesting of the two, because it
counted perfectly well and still did not work. Radio Browser does not record who
owns a station, so unlike a city or a format there was no way to ask it for one;
the folder had to be built call sign by call sign from Wikidata's capped slice,
and roughly three owner folders in four opened to nothing, or to three stations
out of a company's several hundred. A listener spends the same keystrokes on a
folder whether it pays off or not, so an axis that pays off a quarter of the time
is worse than an axis not offered.

Everything here is labelled **from Wikidata** on every row, and it should be,
because the join between the two sources is Quill Radio's own rather than
something either publishes. Nothing here changes how a station plays, records or
is favorited -- the stream is still Radio Browser's.

### 5.7 My Servers: why an empty server is not saved

An address that answers with nothing is deliberately **not** saved. A branch
that is empty the day you add it is nearly always a wrong address, most often a
missing port number, and keeping it would just leave a row that never does
anything.

One honest note on security: a great many small Icecast boxes are plain `http`
on a high port and always have been. Quill Radio accepts those here rather than
refusing the entire audience this branch exists for. It is an address you typed
yourself, nothing is sent but a request for the station list, and no password is
ever attached to it.

### 5.8 Networks, and syndication without a stream

Each list is drawn live from the Radio Browser directory, so there is nothing
new to keep up to date and no new place your searches go. Syndication services
that have no single stream of their own -- Westwood One, NBC News Radio, ABC
News Radio -- open a search across their local affiliate stations instead, and
the label says so.

---

## 6. Finding things

### 6.1 Predictive prefetch

The tree got quicker in a way you will feel rather than see. Land on a collapsed
folder and Quill Radio starts fetching its contents immediately, in the
background, so the expand that usually follows opens instantly; open a folder
and its first few child folders fetch behind it, so walking downward stays ahead
of you.

It is driven entirely by where your cursor actually is -- a source you hide is
still never contacted, and Safe Mode still fetches nothing.

### 6.2 Emptying the search boxes empties the results

Delete your query and the old matches used to sit there looking current -- stale
rows for text that no longer exists, indistinguishable from live ones to a
screen reader arrowing the list. Clearing the name and tag now clears the
results at once and says so. A chosen country keeps them, because a country
facet on its own is still a live query.

The same rule now holds on every search surface in the family: the book library,
weather locations, Spotify, all of them.

### 6.3 No checkboxes in the source pickers

Each row in Search Sources and Choose Browse Sources says its own state and what
the source is: "On. YouTube. Videos, added as stations you can play and record."

There are no checkboxes, because checkbox state inside a list is announced
inconsistently across NVDA, JAWS and Narrator -- and on/off is the one thing
these dialogs exist to tell you. **Turn On or Off** flips the row you are on and
says what happened.

Two further details are deliberate. Hide everything and Browse Stations does not
open onto a blank window -- one row tells you exactly how to get your sources
back. And the choice is stored as *your* choice, so a source added in a future
version appears on its own for anyone who never touched the setting, instead of
being frozen out by a list written before it existed.

---

## 7. Downloads

### 7.1 The queue, and why finished rows stay

Each row is a sentence with its state last, because when you are arrowing a list
you already know what the items are and what you are looking for is where each
has got to.

Finished rows stay until you clear them, because *"did that actually
download?"* is the question people ask most and a list that tidies itself away
cannot answer it. **Open Containing Folder** takes you to a saved file; a
download you cannot find is a download that did not really happen. Cancel one,
remove one, clear the finished or clear the lot -- and every one of those keeps
whatever is already on disk.

**Close the window and it keeps going**, if that is what you asked for. Either
way Quill Radio says which: a queue that silently keeps running is exactly as
surprising as one that silently stops, and which happens is a preference you set
once and will not remember at the moment it matters.

### 7.2 Stopping, and part-finished files

Stop takes effect inside a chapter rather than at the end of a 90 MB one, and
everything already saved stays saved. A part-finished *file* picks up where it
stopped instead of starting again.

### 7.3 Asking once per book

The *ask me where* mode asks **once per book, never once per chapter** -- and if
you cancel the ask, nothing is queued, said out loud, rather than quietly filed
somewhere you just declined.

A live sentence at the bottom of Download Preferences always answers the only
question that matters there: *what will happen to the next thing I save?* The
same window is one button away inside View > Downloads, because that is where
the question occurs to people.

---

## 8. Transcripts

### 8.1 The checkbox that shipped and was removed

A "Follow the audio as it plays" checkbox shipped in the transcript reader at
first and was removed. A cursor that moves while you are reading is a cursor you
are fighting, and everything it offered is better served by Find, which takes
you to a moment you chose rather than the one that happens to be playing.

### 8.2 YouTube captions stopped being thrown away

Every time Quill Radio resolved a YouTube link it also received that video's
caption track, and discarded it. That format is now understood alongside WebVTT,
SubRip and Podcasting 2.0's own format, so a YouTube video's transcript costs
nothing extra to obtain -- it had already been downloaded and dropped on the
floor.

### 8.3 One reader, not two

The plain-text form of a transcript is now *defined* as the timed form with the
timings removed, so there is one reader rather than two that drift apart, and
every transcript Cast could read before reads identically today.

---

## 9. Video

### 9.1 Two things deliberately not built

**No YouTube web player.** It would bring a browser engine, its accessibility,
its adverts and its tracking into an app that exists to avoid all four.

**No video downloading.** Recording still captures audio.

### 9.2 Why the status line does not announce itself

The status line beneath the picture is text you read when you want it, not
something that announces itself. A position display that speaks constantly is
the single most common way a media player becomes intolerable.

### 9.3 The YouTube notice changed, and nobody is asked twice

It used to say Quill Radio contacts YouTube "to find the audio stream behind the
page". That stopped being the whole truth, so it now says audio *or video*, and
says the rights reminder more firmly, because video raises more of those
questions.

Anybody who already agreed is not asked again -- consenting to YouTube is
consenting to YouTube, and asking twice for a superset of the same thing is
friction rather than ethics. Which is exactly why it is written down here.

---

## 10. Sound: the built-in chain and the real engine

Everything in this section is built on **OptiLab Core**, the free accessible
broadcast and mastering engine by **Lanes Audio / dgl1984**
(<https://github.com/dgl1984/optilab>), used here with thanks and under its
Apache-2.0 with Commons Clause licence.

### 10.1 What changed in the built-in chain

If you use **Stream Polish** for music, its Auto-Adapt slider behaves better
now, particularly at the top.

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
range, and the whole chain now delivers to OptiLab's -0.1 dBFS target.

**Podcast Leveler** and **Smooth Limiter** are untouched: this release's
Auto-Adapt work is specific to Stream Polish.

### 10.2 The honest limit of a filter chain

Reproducing the shape of those modes has one limit worth stating plainly.
OptiLab eases its lift and pulls back bass assistance *while* its final limiter
is working hard. A filter chain cannot do that: nothing in it can see how hard a
later stage is working, so there is no way to react to it. Faking the effect
would have meant guessing, and a guess dressed as a feature is worse than an
absence.

There are smaller differences too -- the chain has none of OptiLab's gated
automatic gain control, its six-band density processing, its adaptive bass, or
its hybrid final stage, and Quill Radio's Podcast and Limiter modes deliver to
their own ceilings rather than OptiLab's.

### 10.3 Why "while listening" is the option with a cost

The engine is a separate program, and Quill Radio's live playback never hands
audio to anything else: it tells the player what to apply and the player does
it, which is exactly why every slider you move is audible instantly, with no gap
and no reconnect.

Running the real engine while you listen means routing the stream *through* that
program -- decode, process, re-encode -- so the station takes a moment longer to
start, uses more of your processor, and, most noticeably, **needs a moment to
reconnect every time you change a setting**. The engine is set up with its mode
when it starts and cannot be re-tuned in mid-flight. It is a genuine trade, so
it is a choice you make, not one made for you.

Saving has none of those costs: a recording is processed once, *after* it
finishes. And because it happens afterwards, nothing that goes wrong in the
engine can ever affect the recording itself -- the original is only replaced once
a good processed copy exists.

| | Built-in chain | Exact OptiLab |
| --- | --- | --- |
| Where it can run | Everywhere -- live, relayed, recorded | Everywhere, but live costs a reconnect on each change |
| Hear changes as you make them | Yes, instantly | Only on saved files; live needs a moment |
| Limiter feedback loop | Absent -- the chain cannot react to its own limiter | Present |

Everything else -- the equalizer, Even Out Volume, channel mode, night mode --
applies exactly as before whichever setting you choose. If your build does not
include the OptiLab component the option is disabled and tells you so.

---

## 11. The transport rebuild

### 11.1 Four keys moved, and it matters why

Speed and chapters used to sit on Ctrl+Alt+arrow. That block belongs to JAWS's
and NVDA's table navigation, so those verbs worked everywhere *except* while
somebody was reading a table -- the kind of fault that never gets reported with
a reproduction because it looks like the screen reader's doing.

They are now Ctrl+Shift+Up and Ctrl+Shift+Down for speed, Ctrl+Shift+comma and
Ctrl+Shift+period for chapters, and a build check fails if anything lands back
on that block. Where Am I is Ctrl+Shift+W.

### 11.2 One volume, one distance, one sentence

Volume had drifted into three different behaviours depending on which window had
focus:

- It moved **10** through the menus and **5** through the shared keyboard.
- It said **"Radio volume 45"** in the main window and Find Stations, **"Volume
  45"** in the Recordings list, and **"Volume 45 percent."** everywhere else --
  the Recordings list dropping the unit entirely, so you had to already know the
  scale.
- And Volume Up **while muted** announced a level you could not hear: the level
  changed, the mute did not lift, and nothing came out.

One implementation now, one distance (10), one sentence ("Volume 60 percent.",
"Volume off.", "Muted."), and a deliberate volume change always lifts mute.

### 11.3 No verb listed twice

Each Command Palette entry runs the same dispatcher the keys and the menus run,
refusals included -- and no verb is listed twice, because two
identical-sounding rows in a list somebody arrows through is worse than the gap
it filled.

---

## 12. Recording

### 12.1 Joining the parts, in an order that cannot lose audio

When a stream drops mid-recording, Quill Radio reconnects and continues into a
"(part 2)" file, and now stitches the pieces back into a single recording under
the name you expected.

The join is a straight copy, so nothing is re-encoded and even a long capture
takes seconds. It is done in an order that cannot lose your audio: the joined
file is written, verified, and only then put in place, and the parts are removed
only once that has demonstrably worked. Anything that goes wrong -- a missing
part, parts in different formats, an FFmpeg error -- leaves every part exactly
where it is. You are told either way: "Joined 3 parts into one recording", or
"Kept 3 separate parts" and the reason.

### 12.2 Noticing a recording that stopped recording

A stalled stream can leave FFmpeg alive and apparently healthy while the file
stops growing, so the recording looked fine and captured nothing.

Quill Radio now watches the recording file's size as a second, independent
check: if it has not gained a byte across four checks in a row -- about a minute
-- the recording is treated exactly like a dropped connection. It is patient
enough that a slow network or a station's own rebuffering is never mistaken for
a dead one, and it is never applied to a recording you have just asked to stop.

### 12.3 A late start does not run late

A recording that starts late does not run late at the other end. Quill Radio
records the time that is *left* in the window, so an 11:00 to 2:00 recording
that starts at 11:03 still stops at 2:00 rather than overrunning into whatever
you scheduled next.

That is also why a late start costs you the beginning rather than the end -- and
why, if you want a cushion before a show, the thing to do is start the schedule
earlier **and** lengthen it by the same amount.

### 12.4 The scheduled list, ordered by what happens next

The scheduled-recordings list is ordered by when each recording next occurs,
soonest first, rather than the order you entered them, and each row shows the
stream's host in brackets so two similar entries -- or a duplicate still
pointing at the original station -- are easy to tell apart.

---

## 13. Winamp's keys, and the queue they needed first

**R**, **S** and **Ctrl+V** were held back on purpose. All three -- shuffle,
repeat, stop-after-current -- describe a play queue, and the recordings list did
not have one. Binding them to something that only looked like it worked would
have been worse than leaving them unbound, because you cannot tell a key that
does nothing from an app that is broken.

The list has a queue now, so they are bound.

**Shuffle (R) is a fixed order, not a fresh roll each time.** That distinction is
the whole feature. "Pick one at random on every Next" eventually plays the same
recording twice before it plays some others at all -- and, far worse here, **Z**
cannot take you back to what you just heard, because nothing recorded where you
had been. Shuffle instead reorders the whole list once: every recording plays
exactly once before any repeats, and previous is the exact inverse of next.

**Repeat (S)** cycles off, then all, then this recording. Repeat-one applies when
a recording *finishes on its own* -- pressing **B** still moves you on, because a
Next that refused to move would look broken rather than deliberate.

**Stop after current (Ctrl+V)** is a one-shot. It outranks repeat, because it is
the thing you asked for a moment ago rather than a standing preference; it clears
itself the instant it fires; and it is deliberately *not* remembered between
sessions. A stop that survived a restart would halt playback for a reason nobody
could remember asking for.

Seeking needs something with a timeline, which means a finished recording on the
mpv engine; on a live stream, or with the classic Windows Media engine, the seek
keys say why they cannot move rather than silently doing nothing. A letter typed
into a text field is never swallowed.

The map itself lives in one small shared module with no wx in it, so anything
else in the family that grows a transport can adopt exactly these keys instead of
a second, subtly different set.

---

## 14. Things that were quietly wrong: the full account

### 14.1 A reconnect counted its attempts out loud, to nobody

Quill Radio has retried a dropped live station three times since this release was
first written, and the code that does it composes exactly the right sentence:
*"Reconnecting to KFI AM 640. Attempt 1 of 3."* It writes that sentence into a
field that nothing spoke and nothing displayed.

So what a listener actually got, when a station dropped, was one sound and then
up to twenty-two seconds of silence while three attempts came and went -- which
is indistinguishable from the app having hung. The module's own notes said each
attempt "is announced with its number". It never was. It is now: spoken once per
attempt, and shown in the status line at the same time.

### 14.2 The Xiph genre list was losing 412 genres, every single time

The Xiph directory's genre index had grown past a size limit Quill Radio applies
when reading any web page, so the page was being cut off part way through.

The reader is deliberately forgiving of a mangled page -- which is the right
behaviour when a website tweaks its markup, and precisely the wrong behaviour for
a size limit. It degraded in perfect silence: no error, no warning, just fewer
genres, and a *different* number of them on every refresh depending on where the
cut landed.

The limit now fits the page, and a page that ever outgrows it again says so
rather than dropping entries.

### 14.3 The Xiph genre list was also sorted into uselessness

Xiph publishes its genres in order of how many stations use them: various, Pop,
Rock, Dance, 80s, House, Oldies, Electronic, Hits, Jazz.

Quill Radio sorted that alphabetically. So the list opened on `00`, then `00s`,
then `00s Dance`, then `100.1`, then `104.5` -- and Jazz was some three thousand
rows further down.

The directory's own order is now kept. Entries that are plainly not genres are
dropped, and the branch offers the 120 most-used rather than every free-text
string that three thousand broadcasters have ever typed into a field.

### 14.4 A station that hiccuped once was dead

This came in as a report while 3.0 was being finished, and it is the most
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
"Stopped". The repeated five seconds is the same fault caught a moment earlier: a
connection silently re-established replays what it already sent.

Three answers, and it is worth saying what each one does, because they are three
different answers to the same failure.

**The connection heals itself.** The player was given no instruction to reconnect
a dropped read at all, so a single transient failure was final. It now reconnects
at that level, which is where the great majority of these belong -- nothing is
announced, because nothing was lost.

**A dropped station is reconnected, out loud.** When the connection is genuinely
gone rather than briefly interrupted: three attempts, two seconds apart, then
five, then fifteen, each announced with its number. When it works you hear
"Reconnected to KFI AM 640." When it does not, you are told that plainly, with
the honest guess that the station may be off the air. Nothing here retries
silently, because a player that retries in silence is indistinguishable from one
that has hung.

A recording is deliberately excluded. A LibriVox chapter or an Archive episode
reaching its end has *ended*, and reconnecting would replay it. And pressing
Stop, or playing something else, cancels a retry that was waiting rather than
letting it seize playback a few seconds later.

**iHeart stations use their steadier stream.** Given the choice, Quill Radio now
asks iHeart for the progressive form of a station rather than the HLS form: one
long connection with no segment window, no five-second token and no per-listener
session to lose. It removes the failure mode rather than recovering from it.

A note on that third part, because the obvious version of it is wrong. It would
be tempting to always prefer the steadier stream format wherever a station offers
both. But some directories list two addresses for one station that turn out to be
served by two entirely different companies -- and on at least one station, the
second carries a different station id and a music genre where the station is
sports. Quietly playing you a different broadcaster would be far worse than a
dropout. So the steadier form is preferred only when both addresses come from the
same place, which is a good sign they are two deliveries of one stream.

There is also a fourth, smaller change: the network timeout moved from fifteen
seconds to thirty. Fifteen was tight for a playlist that only advances every ten
seconds, and ordinary jitter could brush against it.

### 14.5 A recording that captured nothing said nothing

Reported alongside the dropout above: pressing Record on a station that would not
stay connected gave no confirmation that a recording had started, none that it
had stopped, and left the recordings folder empty.

Two things were true at once. A recording file is created the moment recording
begins -- before a single second of audio arrives -- so "the file is there" never
meant "something was recorded". And when a capture ended having recorded nothing,
Quill Radio treated it exactly like a finished one.

Now a capture that saved nothing is reported as what it is, in words, with the
reason. The empty file is removed rather than left for you to find and wonder
about, and the message uses the error sound rather than the saved sound, so the
two outcomes can never be mistaken for each other. Where the station said why --
it refused the connection, the address is gone, the disk is full, the folder
could not be written to -- you are told that instead of a generic failure. If the
reason genuinely is not knowable, it says that too, rather than inventing one.

### 14.6 TuneIn could hand you an unencrypted stream

When a TuneIn station returned several addresses, Quill Radio took the first one
that was not TuneIn's own un-followable redirect. That is not the same as taking
the best one, and on at least one station in a sample of forty it meant choosing
a plain `http://` address while an `https://` one was sitting right there.

Stream choice is now ranked rather than filtered: not-a-redirect first, then
encrypted over unencrypted. It still prefers a working plain address over an
encrypted one that nothing can play, because an address that plays beats an
address that is merely tidy.

### 14.7 Updating handed you the wrong edition -- and a fresh install could fail to start

If you have ever chosen Check for Updates and been handed the *portable zip* when
you installed Quill Radio properly: it was reported twice, and the second report
is the one that found it. The app decided whether you were "portable" by looking
for an uninstaller next to the running program, and on the shared runtime the
running program lives in your AppData folder, where an uninstaller never sits. So
essentially every installed listener looked portable, forever.

Underneath that were two more. A release publishes four different downloads, and
the choice between them was made by file extension, so a full-edition listener
could be handed the two-megabyte thin setup and a Companion listener an installer
that cannot install their copy at all. And a copy installed over an existing one
looked portable too, because Windows numbers the uninstallers it leaves behind
and only the first name was recognised.

Two related repairs ship with it, and the first is the most serious thing found
all day: **a fresh install could fail to start at all.** The small program that
launches Quill Radio looks for its shared Python engine in one folder; the
installer was putting it in another. Install cleanly onto a machine that had
never seen it, and the app answered "Quill Radio could not find a Python runtime"
and closed. Both sides now agree on one location, and a build check holds them
together. It was found by *running* an installed copy rather than by reading the
code -- each half looked perfectly sensible on its own, which is exactly how it
survived.

The second: an update now actually replaces the program. Before this, updating a
machine that already had the right Python version copied nothing at all and
reported success.

### 14.8 The Close button did nothing

In the standalone app, the Close button in Browse Stations did nothing. Only
Escape worked. That is a peculiar kind of broken: the control that looks like the
way out is right there, and pressing it just... doesn't.

The cause was 3.0's own window model -- these surfaces became real windows so
they could carry the menu bar, and a real window, unlike a dialog, does not
answer a Cancel button on its own. The same fault sat in **Find Stations**,
**Manage Favorites** and **Schedule Recording**. All four now close from the
button, from Escape and from the titlebar, and there is one shared piece of
wiring behind them so a fifth window cannot quietly grow the same hole.

### 14.9 Delete left your cursor nowhere real

Two lists, the same moment, two different wrong answers. Deleting a **recording**
left the list with no selection and no focused row at all -- the refresh restored
the selection by identity, and a deleted row has no identity left -- so arrowing
began again from the top. Deleting a **favorite** jumped to the *first* item in
the tree, which with forty favorites meant you lost your place entirely.

Both now land on the row that took the deleted one's place, or on the new last
row when the one you deleted was last. Delete the only thing in the list and it
says so rather than going quiet.

### 14.10 Everything now ends as a sentence

Seventy-one announcements ended without a full stop -- "Playing WNYC", "Radio
stopped", "Removed recording X". A screen reader applies sentence-final prosody
on a full stop, the pitch drop that marks a finished thought, and Quill Radio
fires announcements in quick succession. Without it, "Playing WNYC" ran straight
into "Volume 60 percent." as one long run-on.

The pattern was inconsistent inside single files, which is the tell that it was
never a decision. All of them now end as sentences, and a build check reads the
source of every Radio module so it cannot drift back.

### 14.11 Smaller fixes

- **Quill Radio remembers your volume, and Ctrl+Up/Down works from anywhere.**
  The player started every session at 100% unless the station was a favorite with
  its own remembered level, so a non-favorite station came back at full blast on
  the next launch. The last level you set is now saved and restored. Separately,
  Ctrl+Up and Ctrl+Down only worked while the favorites tree had focus; they now
  work from any focus in the window -- except inside a text field, where
  Ctrl+arrow still edits text.
- **"Copy What's Playing" and "What's Playing -- Review and Copy" always answer
  you.** With a station playing, both could come back having done nothing at all
  -- no window, no copy, no message -- while with nothing playing they spoke a
  sensible message, which made the bug look inverted.
- **Recording filenames follow the computer's current time zone.** Filenames used
  to keep stamping the zone that was in force when the app launched.
- **Launching Quill Radio no longer crashes on a stray keystroke.** A key pressed
  at the wrong moment during launch could take the app down before its window
  appeared.
- **Exit means exit.** If you close to the tray, choosing Exit -- even from the
  tray menu -- genuinely quits now instead of ducking back into hiding.
- **Install and restart** no longer hangs behind a stray, focus-stealing terminal
  window.
- **Schedule a recording in hours and minutes**, in separate boxes, so three
  hours is simply "3" and "0" with no arithmetic.
- **A playlist file can no longer attack you.** XSPF and ASX are XML from
  strangers, so they are read with entity expansion switched off. A small crafted
  file that would expand to gigabytes of memory is refused out loud instead of
  opened.
- **ASX is read twice**, once properly and once forgivingly for when the file
  will not parse, because in the wild it is frequently not valid XML at all and
  for that format the second case is the common one.

---

## 15. Spotify, in full

### 15.1 Does a free Spotify account work?

**Yes for finding things, no for playing them inside Quill Radio.** The
distinction is worth being precise about, because it is easy to hear "Premium
required" and conclude a free account is useless here. It is not.

**What works on a free account:** searching Spotify from inside Quill Radio;
browsing your saved shows, episodes, tracks and playlists; and everything else in
Quill Radio, which is untouched by any of this.

**What does not:** audio starting *inside Quill Radio*.

**Why -- and what this is not.** This is **not** "free accounts cannot play
Spotify music". Of course they can, and millions of people do every day, in
Spotify's own app, where the advertising that funds the free tier lives. The
restriction is about **where** the audio plays, not whether you are allowed to
listen. There are exactly two ways another app could play a Spotify track, and
both are closed to free accounts:

- The Web Playback SDK, which "requires a Spotify Premium subscription (mobile
  only types of premium subscriptions are excluded)".
- The Start/Resume Playback web endpoint, of which Spotify says: "This API only
  works for users who have Spotify Premium."

So with a free account, use Quill Radio to *find* things -- which is the part
that is genuinely hard with a screen reader -- and play them in the Spotify app.
Quill Radio tells you which kind of account you signed in with, immediately,
rather than letting you discover it when a track silently refuses to start.

On a Spotify row, Shift+F10 offers **Open in Spotify**. That is deliberately not
called "Open Website": on a free account it is not a footnote about a station's
home page, it is *how you play the thing*.

A Spotify selection can never be **recorded** or **downloaded** on any account,
unlike every other station in the app: the audio is copy-protected.

### 15.2 What you need

1. **A Spotify account** -- free or Premium, per above.
2. **Your own Spotify Client ID.** Quill Radio ships no shared identity, so
   nothing of yours passes through anyone else's account.
3. **Windows with the Edge WebView2 runtime**, which current Windows already has.

### 15.3 Getting your Client ID, step by step

1. Go to the **Spotify Developer Dashboard** at
   `https://developer.spotify.com/dashboard` and sign in with your ordinary
   Spotify account. There is no charge, and this works with a free account.
2. Choose **Create app**.
3. Give it any **App name** and **App description** you like. "Quill Radio" is
   fine.
4. In **Redirect URI**, enter exactly this, then press **Add**:

   `http://127.0.0.1:43217/callback`

   It must match character for character, including the port number. This is how
   Spotify hands the finished sign-in back to your own computer; it never leaves
   your machine.
5. Under **Which API/SDKs are you planning to use?**, tick **Web API** and **Web
   Playback SDK**.
6. Accept the terms and choose **Save**.
7. Open your new app's **Settings**. Your **Client ID** is shown there -- copy
   it.

   You will also see a **Client secret**. **You do not need it**, and you should
   not paste it anywhere. Quill Radio signs in with the modern PKCE flow, which
   is designed precisely for apps that cannot keep a secret.

### 15.4 Where to put it

1. **Station > Connect to Spotify...**
2. Paste your Client ID into the **Client ID** field.
3. Choose **Connect**. Your browser opens Spotify's own approval page: you are
   signing in to Spotify, and your password is never typed into this app.
4. Approve access. Spotify returns you to a small address on your own machine
   (`127.0.0.1`) that Quill Radio listens on for that one moment.
5. Your sign-in is stored in the **Windows Credential Manager** -- never in a
   plain file, never in a log -- alongside your Client ID, so the whole
   connection lives in one place and clears together.

You do this once. Afterwards, **Station > Browse Spotify...** opens a search box
and a results list you can arrow through and play with Enter.

Nothing reaches Spotify until you deliberately connect an account, and the whole
feature is refused in Safe Mode. If you would rather not see it at all, turn
**Spotify** off in Manage Individual Features and its menu items disappear.

---

## 16. Underneath the browse tree: why the next source will be easy

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

That is the difference between "we added a few sources" and "the next one costs
an afternoon".

Three smaller things came with it.

**An empty branch tells you which kind of empty it is.** "There are no stations
in this genre" and "that directory could not be reached" used to look identical.
That is how a listener concludes a working source is broken -- or, worse, decides
a broken one is simply empty and stops checking.

Two ways that distinction was still slipping through, both closed here. Every
source wraps its own network errors in its own error type, and the check that
told the two apart only examined the outermost one -- so when LibriVox went down
for a day, every one of its shelves said *no data in this folder* rather than
*could not be reached*. And the Internet Archive answers a failed search with a
**success** code carrying an error message inside it, which read as "zero
results": Radio Programs reported itself empty, and because an empty answer
looked like a real one it was **cached**, so it kept reporting empty long after
the Archive recovered. Empty answers are no longer stored, and an error inside a
success is treated as the outage it is.

**A slow branch says it is still working.** It names what it is loading --
"Loading Old Time Radio..." -- and if it passes three seconds it says so out
loud, because slow and stuck are the same experience in silence. LibriVox also
gives up in eight seconds now rather than twenty: a browse click was using the
timeout meant for downloading an entire book.

**Browse levels are remembered between sessions.** Opening a source used to fetch
its whole index again every single time, and some of those are very large. They
are kept now, so a branch opens straight away; a refresh that fails leaves you
with what you had rather than an empty branch, and anything shown from memory can
tell you how old it is instead of quietly implying it is current.

---

## 17. Knowing when someone else's service moves

Quill Radio depends on eighteen services it does not control. Historically the
way we learned that one of them had changed was that something stopped working
for somebody.

Each of them is now checked automatically, thirty-seven checks in all, and each
one asks a real question rather than "did the server answer". Not *is it there*
but *did asking for that station give back an address that actually plays*.

Building those checks found three faults before any of this reached you: a
podcast category that came back completely empty when it should have held dozens
of shows, a country list that quietly reported having no regions at all, and a
directory that gave a different answer half an hour later.

All three would have shipped. Two would have looked like "that part just doesn't
find anything", which is the hardest kind of problem to report and the easiest to
put up with.

---

## 18. Quillins in Quill Radio

Quill Radio can run Quillins -- QUILL's small, sandboxed, permission-gated
add-ons -- from its own Quillins menu. A Quillin declares which apps it is for,
so only add-ons written for the radio appear. One thing a radio Quillin can do is
contribute an extra station directory, which then shows up alongside Radio
Browser and the others when you search.

Off in Safe Mode; third-party Quillins stay disabled in this release.

---

## 19. The shared runtime, and the data folder

### 19.1 Why one engine for the family

Quill Radio, QUILL, Quill Weather and QUILL Audio Studio share **one** Python
engine, installed once per user. The runtime is reference-counted, so it is
removed only when the last app that relies on it is uninstalled: uninstalling
Quill Radio while Quill Weather is still around leaves the shared engine in place
for Weather.

The media tools an app declares ride in the runtime's tools folder -- ffmpeg for
Cast, ffmpeg and mpv for Radio and Studio -- so the no-media apps strip them from
their payload and build order can never sneak hundreds of megabytes into a
forecast app.

### 19.2 The data folder, and the one rule a sync client cannot enforce

Everything the Quill family remembers about you lives in one shared data folder,
and **Preferences > Data Folder...** chooses where. Point it at something
Dropbox, OneDrive, Google Drive or iCloud already syncs and your whole setup
follows you from desk to laptop.

The move happens at the next launch (a restart is offered) so nothing shifts
under a running app, and your existing data is carried over for you. The
heavyweight, regenerable machinery -- the Station Catalog, the directory caches
-- deliberately stays on each computer instead of churning megabytes through your
sync service for data the other machine would rebuild anyway.

And the one rule a sync client cannot enforce, Quill watches for: run Quill
against the same folder from two computers at once and the next launch tells you
plainly -- "this data folder was in use on LAPTOP-X two minutes ago" -- instead of
letting two machines quietly fight over one profile.

### 19.3 The icons

Quill Radio's icon was never the problem. The problem was that it was also Quill
Inkwell's icon, Quill Weather's icon and QUILL Audio Studio's icon --
byte-identical copies of the same file, not similar drawings. On a desktop with
more than one Quill app installed, four different products wore one face in the
taskbar, in Alt+Tab, in the Start menu and in the notification area. Nobody chose
that; each new app was built from the last one's template, and an icon is easy
not to notice.

Every app has its own now, and they are still recognisably a set: one rounded
tile shape, one gold accent, one bold picture. What separates them is deliberate
on two axes at once -- a distinct silhouette *and* a distinct colour that differs
in lightness as well as hue, because a set separated only by hue is a set that
some colour-blind users cannot tell apart, and colour is the first thing to go at
small sizes.

Radio keeps the design it always had -- a source with waves leaving it, on a deep
indigo tile -- redrawn for the size that actually matters. At 16 by 16 pixels,
which is the notification area and the small icons in a file list, the old three
thin arcs merged into a single smear. There are now two, thicker and further
apart.

---

## 20. When a media tool goes missing

Two programs do the heavy lifting inside Quill Radio: **mpv**, which plays, and
**FFmpeg**, which records. Both ship inside every installer. Neither is supposed
to be able to go missing.

They can, though -- antivirus quarantine and a half-finished update are the two
usual ways -- and until now Quill Radio's answer to that was **silence**.

The playback engine setting defaults to "automatic", which means "use mpv when it
is there". When it was not there, the app quietly fell back to Windows Media and
said nothing. There *was* a message about it, but only somebody who had gone into
Preferences and demanded mpv by name would ever hear it. Everybody else got a
radio that had lost live pause and rewind, choosing which sound card plays,
Volume Boost, Sound Enhancements without the local relay, track titles from the
stream, knowing when a stream has stalled, and every Ogg Vorbis, Opus and HLS
station outright -- with nothing anywhere saying why.

Now a damaged installation says so, **once**, at launch: one plain sentence
naming which tool is gone, what it costs you, and what to do. It is spoken rather
than shown in a box you have to dismiss, because a launch is not the moment to
grab focus a screen reader has not settled yet.

Three details that matter more than they look:

- **A healthy installation says nothing at all.** An app that reports "all is
  well" on every launch is an app nobody can listen past.
- **It does not nag.** It remembers *which* tools were missing, not merely that
  it has spoken. So it stays quiet on the next launch -- and speaks up again if a
  *second* tool goes missing later, because that is new information.
- **A station that cannot play at all now says why.** An Ogg, Opus or HLS station
  on an installation without mpv used to report "that stream could not be opened"
  -- true, and useless, because the station was fine. It now names the format, the
  missing engine and the fix. Deliberately narrowly: an ordinary MP3 station that
  is simply off the air is never blamed on a missing component.

Either way, reinstalling Quill Radio restores both tools, and **Help > Get
FFmpeg...** fetches FFmpeg on its own.

---

## 21. Song History, and what it will not do by itself

**Song History** (**Ctrl+Shift+H**) keeps a per-station list of every track
change Quill Radio noticed, newest first, with the time you heard it. Each entry
reads as a whole sentence -- "Your Song by Elton John, heard 10:04, played
twice".

From any song you can **Copy** it, **Send to Clip Library**, or ask for
**Background**: a short note about the song and artist from whichever AI provider
you have set up. That answer is always introduced as written by an AI model
rather than by the station, because it sits inches from the station's own
information and the two must never be confused. It is never available in Safe
Mode.

**Song Details** answers the two questions people actually ask about something
they just heard: which release it came from, what year it is, and how long it
runs. It uses MusicBrainz, which needs no key and no account, and it is
deliberately a button rather than something that happens by itself. A history
window that quietly made a network request for every row would be spending your
connection on curiosity you never expressed. When nothing is known it says
exactly that -- "MusicBrainz has nothing more about that song" -- rather than
showing you an error about a server.

The log is yours and stays on your machine: up to 200 songs per station, one
station's listening never pushing out another's, and **Clear...** empties one
station or all of them. A song still playing when the poll comes round again
folds into the entry already there with a play count, rather than filling the
list with the same title six times, and stations that broadcast their own name,
"Live", or an advert marker instead of a track are left out.

---

## 22. The seven questions the app could not answer about itself

These came out of a product review of Quill Radio written before 3.0 landed.
Read back against the shipped app, most of what it recommended was already
built, a few things had been deliberately decided against with the reasoning
recorded in the code, and seven were genuinely open. Each is small; each is a
question somebody can ask that the app had no way to answer.

### 22.1 A safety cap is not a deadline

Every recording carries a `minutes` value, so "how long is left" looks like a
subtraction anybody could write inline. It is not, because that number means
two different things. When the listener asked for a length -- a scheduled
recording, or a duration typed into Record Station -- the end is a **decision**,
and counting down to it is telling somebody what they asked to be told. When
they pressed Record Now and asked for nothing, the recorder fell back to
`settings.max_duration_minutes`, a cap that exists to stop a forgotten capture
filling a disk. Counting down to *that* announces an intention nobody ever
expressed: "142 minutes left" reads as a plan, and somebody who pressed Record
Now has no plan and is owed no number.

So `JobSnapshot` now records which of the two it was, and the status cell
counts down only for the first kind and up for the second. Two details follow
from that and are easy to get wrong. A reconnect is always handed the
*remaining* minutes as an explicit duration, so re-deriving the flag at that
point would silently promote every reconnected open-ended capture into one with
a deadline -- the flag is carried across instead. And elapsed time floors while
remaining time ceilings, so "18 min so far" means at least eighteen have passed
and "12 min left" means no more than twelve remain; rounding both the same way
would make one of them overstate.

### 22.2 A search is not a string

Find Stations has three fields, and they compose. Remembering "jazz" would hand
back the wrong search to somebody who had run it in two countries, so an entry
is the whole triple and revisiting one restores all three fields together.

De-duplication is case- and space-insensitive because "Jazz " and "jazz" are one
intention typed twice, and two rows a screen reader reads identically are
indistinguishable rather than merely untidy. The history rides
`radio_history.json` -- the file that already holds the recently-played list --
deliberately, so somebody clearing that history clears this too rather than
discovering a second one they did not know about.

One subtlety in the wiring. Every keystroke through the Tag combo or the Country
choice fires a search of its own, and remembering those would fill the list with
the half-formed queries somebody passed through on the way to the one they
meant. The dialog already distinguished the two -- it is the same test that
decides whether to move focus to the results -- so the history reuses it rather
than inventing a second notion of "a real search".

### 22.3 Three routes to a title, presented as one

The ICY block is carried with the audio. The player's `media-title` is what HLS
provides instead. The station's status page is a snapshot published for its own
listing, and can lag the audio by a song. Those are not equally direct claims,
and the app made all three identically confidently.

The second half is the rendering. `now_playing.render_now_playing` digs a song
and artist out of whatever the station sent, which is frequently
`text="..." song_spot="M"` and a call sign. That is a *reading*, and when the
reading differs from the original the listener is entitled to both. The module
compares the two rather than trusting a flag, because the rendering is a pure
function of the raw text and asking whether it changed anything is a more
reliable answer than a boolean somebody has to remember to set at each of three
call sites.

### 22.4 The check the directory was already publishing

Radio Browser checks every stream it lists and publishes `lastcheckok`. Quill
Radio parsed the search response on every query and dropped that field. So a
results list made the same silent promise for every row.

Two design constraints kept this honest. **Nothing is scored.** It would have
been easy to rank rows by bitrate, votes and codec and call the result
confidence; that is a guess wearing the clothes of a measurement. The only
negative verdict is the listing directory's own. **Absence is not bad news.**
Only Radio Browser publishes a check, so treating "no check" as a warning would
badge nearly every row in the app to convey nothing -- the rule is the one the
missing-media notice already follows, that a healthy row says nothing at all.

The tri-state matters more than it looks, which is why the field is parsed as
`True` / `False` / `None` rather than collapsing to a boolean: "nobody has
checked" and "the check failed" are the difference between a row that stays
silent and a row that warns somebody off a station. And `last_check_ok` is
excluded from the model's equality, because favorites de-duplicate on the model
and a station that became a *different* station when the directory re-checked
it would quietly duplicate somebody's list.

### 22.5 Told versus asked

`media_preflight` speaks once at launch, never modally -- a launch is not the
moment to take focus a screen reader has not settled yet -- and remembers *which*
tools were missing rather than merely that it spoke, so a second loss is news
and the same state is not repeated forever. All of that is right, and all of it
is the app deciding when to talk.

Audio Health is the same facts asked for. Two rules shape it. **It probes
nothing**: no test tone, no device opened, no file written, because a
diagnostic that changes what it measures is worse than none and because
somebody opening it mid-recording must not disturb the recording by looking.
Writability is checked with `os.access` rather than a temp file for exactly
that reason. **It does not grade**: no score, no traffic light. A green tick and
a number at the top would invite somebody to trust the summary over the
sentences under it, and the sentences are the product.

It also reuses `media_preflight.current_health` rather than probing separately,
following that module's own warning: a health report that asks a different
question from the code it describes will eventually describe a machine nobody
has.

### 22.6 A shortcut list that cannot go stale

The sheet does not read the keymap. It reads the menu bar the listener is
looking at, which is stronger in three ways: it covers items whose keys are
literals rather than keymap entries (F1, Shift+F1, the Recently Played rows);
it cannot drift, because there is no second copy to keep in step -- the failure
mode that has put a stale shortcut table in every manual ever written; and the
menu-accelerator gate already guarantees every enabled item carries a unique
key, so the list is complete and unambiguous by construction rather than by
hope.

Disabled items are skipped. A disabled item is a status readout, and it is also
the one case the accelerator gate exempts from carrying a key, so listing it
would produce a row with nothing to press. The handful of keys with no menu
item are hand-kept data and marked with the surface they work in -- the one
second copy in the design, deliberately tiny, because a wrong row there means
somebody pressing a key that does nothing and concluding the app is broken.

### 22.7 The window that was not built

The obvious reading of "there should be one recording center" is that the
Recordings window and the Schedule window want merging. Building that would
have made the app worse, and the reasoning is worth recording because the
obvious thing was wrong.

`recordings_index.list_recordings` already returns **one** list holding active
captures, finished files and scheduled entries together, and the Recordings
window already showed all three with counts and the output folder. The two
windows are not two views of one thing: one is the shelf, the other is the form
you fill in to add to it. A third window showing the same list again is exactly
the second surface that drifts from the first -- which this project has paid for
in two transcript readers, two copies of the search-within-a-folder knowledge,
and four apps wearing one icon.

What was actually missing was one fact: the window could tell you there were
three scheduled recordings and could not tell you when the next one was. That
lived only inside the scheduled rows. So the fix is a better sentence, not a
new surface -- and it reuses the recording-progress module rather than
re-deriving elapsed and remaining, so the headline and the status-strip cell
can never disagree about the same capture, including on the point that an
open-ended one has no deadline.

### 22.8 What the extractions say about the seams

Three modules went over the GATE-11 budget, and the gate's own instruction is
to extract rather than raise. Each split follows a real seam rather than a line
count, which is the only way an extraction leaves the tree better than it found
it: `ui/radio/search_recents.py` (everything about remembered searches),
`ui/radio/results_view.py` (everything about what a result row *says* -- which
is where per-row confidence naturally landed, since a badge in the row and a
sentence in the panel are both presentation), and
`ui/main_frame_radio_status.py` (the read-only status windows, which turn out to
have a theme: every one of them exists because the app otherwise only speaks
when it decides to).

---

*The story version of this release is in `release-notes-3.0`, which ships in this
same `docs` folder.*
