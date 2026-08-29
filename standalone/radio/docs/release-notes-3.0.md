# Quill Radio 3.0 Release Notes

There is a moment, early on, that decides how somebody feels about a piece of
software. It is not the moment they discover the clever feature. It is the
moment just after they open it, when the app either tells them where they are
or leaves them to work it out.

Quill Radio 2.1 left you to work it out. It opened on an empty favorites tree
-- an accurate picture of having no favorites, and an answer to none of the
questions anybody actually arrives with.

So that is where this release starts, and it is where these notes start too.
What follows is a story in two parts. The first is your first hour with Quill
Radio 3.0, told from the beginning, assuming nothing. The second is for
everybody coming from 2.1.2 who already knows this app and wants to know what
moved underneath them.

Read the first part even if you are the second kind of reader. A good deal of
3.0 is in it. And it ends where the app is going: how Quill Radio sits beside
QUILL Cast, what each of them is for, and what is being built next in each.

---

## Part One: Your first hour

### The first minute

Open Quill Radio for the first time and it introduces itself. Three screens.
Not seven -- three.

1. **Welcome to Quill Radio.** What it is, that it is built for listening with
   a screen reader, that nothing here needs an account and nothing you listen
   to leaves your computer, and the one key that carries most of the app.
2. **Find something to listen to.** The three ways in: Browse Stations, Search
   All Sources at the top of that tree, and Add Station for an address you
   already have.
3. **Keep the ones you like.** How favorites work, that the first ten answer a
   key each, and that Radio keeps playing while you work.

**Skip is a real button**, sitting with Back and Next, and skipping counts as
done. Somebody who already knows what an internet radio is should be able to
leave in one keystroke.

**It never runs for somebody who already has favorites** -- an imported station
list, a restored backup, an upgrade from any earlier Quill Radio. Explaining
how to find a first station to somebody with forty is a way of saying nobody
checked.

**Every key it teaches is the key you have.** The screens are rendered against
your live keymap, so if you rebound Browse Stations, it names *your* key.

**And the words are in a text box you can arrow through**, not a wall of
labels. Somebody who missed a sentence can go back over it at their own pace,
and copy it, instead of asking the app to say it all again.

On the second and third screens a **Browse Stations Now...** button takes you
straight out to find something. Taking it counts as finished: somebody who went
and found a station has been onboarded, whatever screen they were on.

#### And then it stays quiet

Behind a checkbox on that first screen -- **Show me a tip now and then** -- are
six things worth knowing that no button label can tell you: that live radio can
be paused and rewound; that Radio remembers a volume for each station
separately; that a recording can be scheduled for a programme that has not
started yet, and will wake the computer to catch it; that Sound Enhancements
can be set for one station rather than all of them; that Browse Stations
reopens where you left it; that Song History keeps every track a station
announced while you listened.

Each appears **once, ever**, the first time you reach somewhere it would help.
None of them takes the keyboard or interrupts you -- they ride the same
announcement path as everything else, so they reach speech and braille and then
they are gone. Unchecking the box switches all of them off permanently.

### Somewhere to start

Press **Ctrl+B** and Browse Stations opens onto thirty branches. In 2.1
there were thirteen.

Four of the new ones are axes the station directory always had and nobody had
ever exposed. **By Country** opens a country, then its states or regions, then
its stations, most-listened first. **By Language** is the same world on a
different axis, and it is the one that is genuinely hard to find anywhere else:
most radio apps organise by where a station *is*, which is the wrong
organisation entirely if the radio you want is not in the language of the
country you happen to be sitting in. **Trending Now** ranks by what is being
listened to today, rather than by votes accumulated over years -- the two lists
disagree far more than you would expect. And **Recently Added or Changed** is
the branch that makes a directory feel alive rather than archival.

The other new branches are whole libraries:

- **Internet Archive** -- Old Time Radio, Audiobooks & Poetry, the Live Music
  Archive, Radio Programs, News & Public Affairs. Old Time Radio alone holds
  8,710 recordings across 114 series.
- **LibriVox** -- public-domain audiobooks, recently added, across 43 genres,
  and by author through some seven thousand of them.
- **Project Gutenberg** -- the 1,124 records that carry human-read audio, by
  topic and by language.
- **Audius, Mixcloud and ccMixter** -- independent music, DJ sets and radio
  shows, and Creative Commons music whose licence rides in the row itself.
- **AudioPub** -- a community where people share audio they made, opening on a
  Discover shelf of fifty, different every time you open it.
- **Explore** -- every station Wikidata knows about, by city, by format, and
  **On the Dial**, which groups stations by where they sit in the FM band.
- **My Servers** -- your own Icecast or SHOUTcast address. The branch no
  directory can give you: the community station three towns over, the church,
  the school, the reading service running its own box. You supply the address
  once and browse it forever, each stream listed with what is playing on it
  right now.
- **Networks** -- the BBC, NPR, CBC, ABC Australia, RTE, RNZ, NHK, Deutsche
  Welle, Radio France and the rest, gathered into one-click lists.
- **YouTube** -- channels, playlists and single videos. More on that shortly.

Twenty-eight branches is a good problem and still a problem. If you only ever
open your local stations and ACB Media, every branch you never use is not
clutter, it is *distance*. So **Station > Choose Browse Sources...** turns any
branch off, and right-clicking a branch offers **Hide This Source** on the
spot. The rule that matters: a branch that is off is not in the tree at all,
and is never contacted. Not hidden-but-fetched -- gone. It is a privacy and
speed control as much as a tidiness one.

Two smaller kindnesses. Expanding a country no longer flings your cursor down
into the stations; you stay on the folder you opened, hear its count, and step
in when *you* decide to. And Browse Stations remembers where you were, so it
reopens on the source you were last in rather than collapsed at the top.

### The radio that works before the internet does

Here is the part that surprises people.

Open By Country and it answers **instantly**. Not "fast" -- instantly, under a
millisecond -- because the answer comes from your own disk. The whole
working-station directory ships inside the app: more than **62,000 stations
across 240 countries**, every genre, language and codec, plus SomaFM and the
complete Project Gutenberg audio shelf. All of it arrives with the app. A first
launch on a machine with no internet at all is a complete radio.

It costs about seven and a half megabytes.

Because counting is now free, every folder tells you its size before you open
it -- "France, 812 stations" -- something the live directory could never afford
to say. Find Stations gains the same superpower: local matches appear the
moment you type, with the live directories layering in behind them. Pull the
network cable mid-search and you still get results.

**And it is honest about its edges.** Some branches stay live, each for a
stated reason -- Apple's charts are rankings its terms bar storing, TuneIn's
directory may not be stored, the Internet Archive's collections would dwarf the
app, and charts are stale the moment they are saved. None of that is buried in
a manual: **View > Station Catalog Status** lays out, source by source, what is
stored on this computer and how fresh it is, and what is not stored and why.
Highlight any branch in the tree and the details panel says either "Answers
from your catalog, updated 2 hours ago" or "Asks the internet each time;
nothing is stored."

If you are offline, the app says so exactly once -- "You are offline. Browsing
from your catalog, updated this morning." -- and then gets out of the way,
because quietly working is the feature.

The catalog keeps itself fresh three ways, each yours to switch off: a quick
check shortly after launch, a scheduled trickle every 24 hours by default, and
**Station > Update Station Catalog** on demand, which always answers out loud:
*"Station catalog updated: 174 new stations, 431 updated. Xiph could not be
reached; keeping what you have."*

That last sentence is the whole philosophy. A directory that is down costs you
its freshness, never your stations.

And your stations were never part of the deal. Favorites, custom stations,
servers, YouTube channels -- those live in their own files, and no catalog
operation reads or writes them. Not carefully avoided: structurally elsewhere.

### Type a title, and everything answers

Browsing is how you find something you could not have named. Search is how you
get to something you can, and in 3.0 it reaches everything.

Press **Ctrl+F**. Type a title. The results carry radio stations, **LibriVox
books, Internet Archive recordings, Project Gutenberg audiobooks, podcasts**,
Audius tracks, Mixcloud shows, ccMixter uploads and YouTube videos -- each row
labelled with where it came from, so a book and a station are never confused.

The libraries answer separately from the stations and **appear as they
arrive**, so one slow library never holds up the rest, and if you are already
arrowing the station results when a library answers, your place is kept.

And what it finds, it plays. A podcast or an audiobook in the results is a
*work*, not a stream -- there is no single address to hand the player -- and
pressing Play on one used to do nothing at all. Now an Apple Podcasts show
fetches its feed and plays the **latest episode**, a LibriVox book plays its
**first section**, each announced by name.

**Station > Search Sources...** switches any of the eight sources off, and a
source that is off is never contacted -- so switching sources off makes
searching genuinely faster and quieter, not just tidier. Your choices are
remembered, because a preference you have to set again on every search is not
really a preference.

**And so are the searches themselves.** Press **Down** in the station-name box
and there are the searches you already ran, newest first. Pick one and all
three fields come back together -- name, tag and country -- because they
compose: *jazz in France* and *jazz in Brazil* are different searches, and a
list that remembered only "jazz" would hand you back the wrong one. Running the
same search again moves it up the list rather than adding a second copy of it,
and an empty search is never kept, because clearing the boxes is how you start
over rather than something to come back to.

**A row that probably will not play now says so.** Radio Browser runs its own
checker against every stream it lists and publishes the answer. Quill Radio has
been downloading that on every single search since the beginning and throwing
it away, so every row in the results made exactly the same silent promise and
the only way to find the dead ones was to press Enter on each in turn. Rows the
directory could not play are now marked "may not be playable", and rows that
have to be looked up before they can start -- TuneIn, YouTube -- say that
instead, so a pause before the audio begins is explained rather than worrying.

Everything else stays quiet, on purpose. Only Radio Browser publishes a check,
so labelling the rest "unknown" would put a word on nearly every row in the app
to tell you nothing. And nothing here is scored or guessed at from bitrates and
vote counts: the only bad news the app will give you about a station is the
listing directory's own.

**Find inside the tree got clever, too.** "Find in this folder" used to walk
the subtree and match whatever happened to be loaded -- honest, bounded, and on
the Podcasts branch useless, because it crawled chart pages and never once
asked Apple's search engine. Find now takes the fastest honest route for
wherever you are standing: the real podcast search API on the Podcasts branch,
your own catalog on a catalog-served branch, and each library's own search
engine everywhere one exists. Every answer says where it came from --
"Searched the whole podcast directory." or "From your catalog." -- because a
fast answer whose origin is stated beats a fast answer you might mistake for a
complete one.

### Press Enter

#### The thing no other desktop player does

A *described* audio track is a second narration mixed into a programme that
says what a sighted viewer can see: who came into the room, what the caption on
screen says, where the scene moved to. Broadcasters publish them as a matter of
course. YouTube carries them on a growing number of videos.

And essentially no desktop media player lets a blind listener find one. The
better ones expose an audio-track menu, and what it contains is "Track 1, Track
2, Track 3". Which of those narrates the picture? The only way to find out is
to play each in turn and listen. That is not a feature, it is a puzzle, and it
is the exact shape of the problem this app was built to stop.

Quill Radio names them.

**Playback > Audio and Described Audio... (Ctrl+Shift+A)** lists every audio
track a video publishes -- "English", "Spanish", "English (described) --
narrates what is on screen" -- with the described one **first**, the cursor
already on it, and a line above the list that says, before anything else you
hear, *"Described audio is available for this video."*

**Playback > Play Described Audio (Ctrl+Alt+D)** skips the list and switches
straight to it.

**And it tells you, without being asked.** Play a video that carries a
described track and Quill Radio says so once: *"Described audio is available
for this video. Press Ctrl+Alt+D to hear the narration of what is on screen."*
Once per video, never repeated, never interrupting.

That sentence is the feature. A command you have to know about only helps
people who already know it exists -- and those are exactly the people who least
need telling.

Three things about it are deliberate. **Switching keeps your place**, because
losing your position an hour into a film to turn description on would make the
feature useless in precisely the case it matters most. **Nothing is promoted
behind your back**: the ordinary track is still right there, still labelled.
And **when there is none, it says so, and says what there is instead** --
*"This video has one audio track, English. No described audio was published."*
-- because "no described audio" on its own leaves you wondering whether the
video is missing it or the app cannot find it, and those are completely
different things to know.

The same door opened every dubbed track. A multi-language video now lists all
its renditions by name -- one popular video offers twenty-four, from Hindi and
Tamil to Japanese and Polish -- each spoken as a language, never as a code or a
track number.

Getting YouTube to hand over those described tracks took a genuine fight. The
long version is in the in-depth companion.

#### Anything with an end has a timeline

A live station is a river; you step in where everyone else is. Anything
finished is the opposite, and 3.0 treats it that way. On any finished video or
recording:

| Key | What it does |
| --- | --- |
| Ctrl+Shift+C | **Chapters...** -- the uploader's own list; Enter jumps to one |
| Ctrl+Shift+comma / period | Previous / next chapter |
| Ctrl+Shift+Left / Right | Back / forward 30 seconds |
| Ctrl+Shift+Up / Down | Play faster / slower (0.25x to 4x, remembered) |
| Ctrl+Shift+J | **Go to Position...** -- Hours, Minutes, Seconds, or type `1:23:45` |
| Ctrl+Shift+W | **Where am I?** -- position, length, and the chapter you are in |

The chapter list reads each entry as a whole sentence -- "3. Introducing
layers, starts at 5 minutes 31 seconds" -- and marks the one playing now.

**Every one of these says why when it declines.** Point any of them at a live
stream and you hear "This is a live stream, so there is no timeline to move
along", not silence. A slider that cannot move and a "next chapter" that
quietly does nothing are worse than not offering them at all, because you
cannot tell a broken control from a stream that has no timeline.

#### Reading instead of listening

A finished video's captions, and a podcast episode's published transcript, can
now be read as text that still knows what time it is. **Playback >
Transcript... (Ctrl+Shift+T)** opens an ordinary read-only text box --
deliberately, so arrow keys, word and line movement, selection and your screen
reader's review cursor all work exactly as they do everywhere else.

What the timings add is everything around the edges. **Your cursor is yours**:
playback never moves it, because you are reading and the audio can wait.
**Enter on any line** jumps playback to the moment that line was spoken.
**Ctrl+F** searches and announces the hit as *"Found at 12 minutes 8 seconds.
Enter plays from here."* -- so the verb that acts on what you just found is the
next key you press. That is the thing a transcript in a text file can never do
for you.

There is a **Links...** button (Ctrl+Shift+L) that lists every web address in
the transcript and opens or copies one, because reading an address out of a
read-only box and retyping it is not a way to follow a link. **Save As** offers
plain text, **WebVTT** or **SubRip**, and **Open in QUILL** hands it over as a
document to annotate or braille.

**An automatic caption track says so, in the heading**, every time. Machine
transcripts are useful and they are not accurate; presenting one as if a person
wrote it would be the sort of confident wrong answer this app refuses to give.

And a transcript is readable **without playing anything**: an episode whose
feed publishes one says "transcript available" on its row and offers **View
Transcript...** on its context menu. YouTube rows do the same.

#### And you can see the picture, if you want it

**Playback > Show Video (Ctrl+Shift+V)**, and the whole design is one sentence:
**video is a view onto what is playing, never a mode of playing.** Closing the
window, or never opening it, leaves Quill Radio behaving exactly as it always
has. Opening it attaches to a stream that is already playing, so it does not
restart anything and **cannot cost you your place**.

Why this matters in an app built for blind listeners: somebody with usable
residual vision, who uses Quill Radio precisely because YouTube's own site is
hostile with a screen reader, was getting audio only. So was anybody wanting to
share what they are listening to with a sighted person in the room.

**The picture reports itself properly.** This is where video players usually
fail: the image is an unnamed window a screen reader lands on and calls
"graphic". Here it has a real name -- *"Video: The Adventures of Sherlock
Holmes, part 4"* -- and a description saying what it is and where the controls
are. It is in the tab order exactly once, Tab always leaves it, and it never
grabs focus by itself.

**There are no on-screen buttons, on purpose.** Every command is on the
Playback menu, in the Command Palette, and on a key you can change. Captions
(Ctrl+Shift+K) default to **solid white on solid black**, because caption text
sits over arbitrary moving pictures and an opaque box is the only honest
default; they scale to 300%, because the standard asks for 200% and a floor is
not a target. The picture can be dimmed for light sensitivity, and the
keystroke that removes it works from anywhere in the app.

### Keep what you find

#### Favorites, exactly the way you arranged them

If you have ever hand-sorted thirty stations into the order that makes sense to
*you*, this part is a love letter. Moving a favorite from a sorted A-to-Z view
no longer quietly overwrites that hand-built order: Quill Radio switches to
manual order, says so, then moves the station, leaving your arrangement intact.

When a long haul of arrow presses feels absurd, **Mark and Move** does it in
one gesture: right-click a station, choose **Mark for Move**, travel to the
destination, and pick **Move Marked Above** or **Move Marked Below**.
**Ctrl+Shift+E** makes a **New Folder** from anywhere. And the first ten
favorites answer a key each -- **Ctrl+Alt+Shift+1** through **0** -- playing
directly without opening anything.

#### Downloads: the things you are allowed to keep

Quill Radio plays a great deal that is genuinely yours -- public-domain
audiobooks, old-time radio, Creative Commons music, podcast episodes published
for exactly this purpose. Until now it could play all of that and save none of
it.

**Download...** on a row's menu saves it. **Download All Files...** on a book's
folder saves the whole thing, chapter by chapter, in order, while you carry on
listening to something else.

**A whole book is the case this was built for.** A LibriVox novel is forty
chapters and forty separate addresses -- an hour of transferring over a
connection that will hiccup at least once. So chapters are fetched **in
order**, which means a part-finished book is the first twelve chapters,
something you can start listening to, rather than a scattering you cannot. One
bad address costs **one chapter**, never the book. Progress is counted the way
a person counts: *"12 of 40"*.

**And it will not save what is not yours to save.** A source has to be
affirmatively allowed; anything unrecognised is refused rather than guessed at.
Where Download is not offered, asking for it anyway tells you which of four
quite different things is true:

| Why it is not offered | What Quill Radio tells you |
| --- | --- |
| It is a live station | There is no file to save -- a broadcast has no end. **Record Station** is the command you want, and it says so. |
| Spotify | Copy-protected. No app can save it, including this one. |
| YouTube | A decision, not a limitation. Quill Radio plays and records; downloading from YouTube is not something it does. |
| Audius | Whether a track may be downloaded is the artist's choice, and the listing does not say. Quill Radio will not guess on their behalf. |

**View > Downloads...** is the queue -- what is waiting, what is going, what
arrived, what failed. Finished rows **stay** until you clear them, because
*"did that actually download?"* is the question people ask most and a list that
tidies itself away cannot answer it.

Where things land is arranged for you and every rule is yours
(**Station > Download Preferences...**): a podcast goes under its show, a book
gets a folder of its own, and an author gets a folder only once you have more
than one of their books -- since an author folder holding exactly one book is a
folder you open and immediately leave. A downloaded book then **plays like a
book**: chapters in order (2 before 10, which is obvious to a person and wrong
in every naive sort), each announcing itself briefly -- *"4 of 40, The Dead
Hand"* -- and the end of a book says so rather than falling silent.

A Creative Commons licence travels with the file, written into a small text
file beside the audio, because saving somebody's work under a licence and
dropping the licence strips exactly the information it exists to carry.

#### Your place, kept

**Playback > Continue Listening...** shows everything you began and did not
finish, newest first, with how far in you are: "The Moonstone, chapter 4,
recording, 10 minutes in, 8% through". Files on your own computer are in the
list too, and your place in a file is remembered by the file's *contents*
rather than its name, so it survives moving and renaming.

Two deliberate refusals: **four seconds in is not a position**, and
**finishing clears it**, so replaying something starts at the start rather than
at the closing credits. A live station never appears at all -- you tune in and
you are where everybody else is, and a radio that offered to "resume" a live
stream would be offering nonsense.

#### And a real backup

**Station > Back Up Stations and Settings...** gathers your favorites,
settings, wake timer and recording schedule -- and, if you want them, your
recorded shows -- into a single `.qrbackup` file. **Restore from Backup...**
brings it all home on a new PC, a new BrailleNote, or a fresh Windows.

Underneath that, your favorites protect themselves: every change snapshots the
previous version aside, and **the last 20 are kept**, so a bad edit or an
accidental delete is never final. That safety net is what makes the Favorites
Manager's **Remove All...** safe to offer at all.

### Make it yours

**One volume, when you want one.** Quill Radio remembers a volume for each
favorite, which is lovely when stations are mastered at wildly different levels
and maddening when you simply want everything quieter. **Playback > Use One
Volume for All Stations** makes a single level answer for everything. Ticking
it adopts whatever you are hearing at that moment, so nothing lurches, and
unticking it puts every station straight back to its own remembered level -- so
trying it costs you nothing.

**Sound, on Ctrl+E.** The three-band equalizer, compressor, channel mode, night
mode and broadcast polish have been here since 1.0.2 and never had a key of
their own. Everything inside previews live as you move a slider. New in 3.0:
Quill Radio can run the **actual OptiLab Core engine** -- Lanes Audio's real
broadcast processing code, included in the build -- rather than an impression
of it. **Exact OptiLab processing** is off by default; "When saving" is the
recommended setting, because a recording is processed once, afterwards, where
taking a little longer costs nothing.

**Everything it says now reaches braille.** What's Playing, a finished refresh,
a recording starting -- all of it is written to a connected braille display,
not only spoken. Nothing is truncated, an identical message inside two seconds
does not steal the display twice, and braille never costs speech: an unplugged
display degrades to "spoke but did not braille", never to silence.
**Announcement Self-Test...** announces a phrase and then tells you which
channels actually delivered it, so "braille is broken" and "no display is
connected" stop looking the same.

**A status bar you can walk into.** **View > Show Status Bar**, then **F6** to
land in it: what is playing, the volume, whether a recording is running and
**how long it has left**, the sleep timer, how many favorites you have, and the
time. Arrow across the cells and press **Enter** on one to *act* -- Enter on Now
Playing opens What's Playing, on Volume mutes, on Recording starts or stops a
capture. **Escape** hands focus straight back to your favorites.

The recording cell is careful about which number it shows you. Ask for an
hour and it counts *down* to the end you chose. Press Record Now, where you
asked for no length at all, and it counts *up* -- "18 min so far" -- because
the only figure it has in that case is a safety cap that stops a forgotten
capture filling a disk, and counting down to that would be announcing a plan
you never made.

**And you can trim the app to what you use.** **View > Customize Features**
turns whole areas on or off, and **Text Size** (Normal, Large, Larger)
enlarges the main window together. Every choice here is remembered.

### When you want to ask, rather than be told

Quill Radio says a good deal at the moment *it* decides: a refresh announces
itself, a damaged installation speaks once at launch, every menu item names its
key as you pass it. All of that helps somebody the app has something to tell.
None of it helps somebody with a question.

Three windows answer questions.

**Audio Health (Ctrl+Alt+Shift+M)** is the one to know about. It answers "is
this going to work?" -- which engine is actually playing (including the case
where "automatic" has quietly fallen back to Windows Media because mpv is
missing, a setting that still reads *automatic* and tells you nothing), whether
mpv and FFmpeg are here and what their absence costs, where the audio is going
and whether the system still offers the device you chose, what Sound
Enhancements are doing and whether they are set for this station or all of
them, and whether a recording started right now could actually be written to
the folder you picked.

It tests nothing. No tone is played, no device opened, no file written -- so it
is safe to open in the middle of a two-hour capture, which is exactly when
somebody wants it. And it counts problems rather than scoring health: there is
no traffic light at the top inviting you to trust a summary over the sentences
underneath it.

**The Keyboard Shortcuts Sheet (Ctrl+Alt+Shift+K)** answers "what can I
press?". 3.0 made every menu item name its own key, which is a real fix while
you are *in* a menu and no help at all when the question is the whole
keyboard -- the only answer to that was opening six menus and arrowing to the
end of each. The sheet is one list, and you can type into it: filter by what
you want to do ("record"), or by a key you found and cannot place ("Ctrl+B").

It is built by reading the menu bar in front of you, which is the part that
matters. Rebind something and the sheet says your key, not the default -- and
it can never drift from the menus, because it *is* the menus. The keys that
have no menu item to carry them -- F6 into the status bar, the Winamp letters
in the Recordings player -- are listed too, each with the window it works in.

**And the columns are yours now (Ctrl+Alt+Shift+C).** This one is a speech
setting wearing a display setting's clothes. A list like Find Stations is read
out one column at a time, so the columns *are* the sentence you hear on every
row -- and that sentence had been chosen once, in code, for everybody. If you
never leave one country you heard a country on all sixty thousand rows. If you
choose stations by who runs them, the source was read last.

**View > Choose Columns...** hands it over, for Find Stations results and for
the Recordings list. There are two lists in the window -- what is shown, in the
order it is read, and what is hidden -- with Move Up and Move Down between them.
Not checkboxes: a checkbox in a list is a state your screen reader has to be
asked for, while a position is a place you land on, and moving something says
where it is now.

Hiding a column takes it *out* of the row rather than to the end of it, because
a screen reader reads every column it is given and "last" is still read. It
keeps its place while it is hidden, so bringing it back a week later does not
send it to the end of a row you already arranged.

Under the two lists, one line reads out exactly what a row will say. That is the
part worth having: you can hear the effect of hiding Country before you press
OK, rather than pressing OK and finding out.

Each list also offers more than it shows, because a list that says everything
says nothing. Find Stations can add Language, Genres, Popularity and Bitrate;
Recordings can add Length -- and Length is deliberately blank where the number
Quill Radio holds is a disk-safety cap rather than a length you chose, because
reading out a cap as a plan would be telling you something you never said. One
column in each list cannot be hidden -- the station's name, the recording's
name -- and asking to says so, and why.

QUILL Cast gets the same window on its own lists, from the same code. Quick
Actions, listening statistics and folder actions all had to be carried across
from one app to the other after being built twice; this one was shared on the
first day.

**The Recordings window now says what happens next.** It used to count things:
"14 recorded, 1 recording now, 3 scheduled". That answers *how many* and never
answers *when*, and when you are checking on a Thursday evening whether
tonight's show is covered, when is the entire question. It now opens with
"Recording, 42 min left. Next: KFI at 11:00 tomorrow. 14 recorded." -- and a
show inside the hour is given in minutes, because "in 12 minutes" tells you
whether you can leave the room. Three schedules that all happen to be disabled
say "none coming up" rather than reading as cover.

**And the full What's Playing window says where the song came from.** Quill
Radio looks for a track title in three places -- the metadata carried along
with the audio, the player's own reading of the stream, and the station's
status page -- and used to present whichever answered as one confident
sentence. They are not the same kind of fact: a status page is something the
station publishes for its own listing, and it can be a song behind what you are
actually hearing. Now it says which one answered.

It also shows you what the station really sent, when that differs from what you
are being shown. Stations pack a great deal into that field -- advert markers,
their own call sign, `text="..."` wrappers -- and the song and artist are read
*out* of it. That reading is usually right and is not always right, and now you
can see both and judge.

---

## Part Two: What moved, if you already knew this app

Everything above is new in 3.0. This part is for the reader coming from 2.1.2
-- what changed shape underneath the app you already knew.

### Stations that are not stations

**Paste a YouTube link into Add Custom Station and it becomes a station.** It
plays through the same player, sits in Favorites, records with Record Now, and
can be captured by a scheduled recording. Quill Radio saves the *page* address,
never a stream address, and re-finds the audio each time -- so a recording you
schedule today still works next week.

It works out of the box: the `yt-dlp` helper is built in, so your first YouTube
link simply plays, with no download and no consent prompt standing between you
and the thing you asked for. When YouTube changes how it serves audio,
**Station > Update YouTube Support...** fetches a newer helper rather than
making you wait for the next Quill Radio release.

Around that grew a whole branch. **Add a Channel...**, **Add a Playlist...**
and **Add a Video...**, or the one-command version -- **Station > Add YouTube
Link... (Ctrl+Alt+N)** -- which files whatever you pasted by what the link
actually is. **Import YouTube Subscriptions...** takes the `subscriptions.csv`
from your own Google export and brings thirty channels across in one step,
with nothing authenticated, no token stored, and no request made to Google at
all. **Add from YouTube Playlist** lists a playlist in the uploader's own
running order, never re-sorted, because a series is meant to be worked through
in order.

**Podcasts, and not a single key anywhere.** Open **Podcasts (Apple)**, choose
a country, and you get that storefront's top shows and Apple's entire genre
tree. Open a show, press Enter on an episode, and it plays. No key, no account,
no registration, no sign-in, nothing to configure first. The top podcasts in
Ireland, or Japan, or Brazil are one folder away, which almost no desktop
podcast client offers.

Apple stops being involved the moment you open a show: a show resolves to its
own RSS feed, and everything after that comes from whoever makes the show.
**Subscribe to This Podcast** files it in the shared podcast library, and the
Subscriptions folder at the top of the branch counts itself -- "Subscriptions
(3)" -- with each show beneath it wearing "(2 unheard)". That library is shared
with QUILL Cast, which is a bigger deal than it sounds; see *Radio and Cast:
two apps, one library* below.

**Paste a Live365 link and it just plays.** The link you actually have is
almost never the stream; it is the station page or the web player. Add Custom
Station rewrites it to the real stream address and tells you it did -- a pure
text rewrite, with no network lookup and nothing sent anywhere.

**Spotify (experimental)** can be searched and browsed on any account tier, and
played inside Quill Radio on Premium. Searching works on a free account, which
is the part that is genuinely hard with a screen reader. The full setup walk --
your own Client ID, why there is no shared identity, and what Spotify's terms
do and do not allow -- is in the in-depth companion.

**Playlists in the formats the internet actually uses.** Quill Radio understood
M3U; a "Listen Live" link is at least as likely to be a `.pls`, an `.xspf` or
an `.asx`. All three now open, favorites export in all four formats, and every
one reads back in. A live stream can no longer be imported as a list of
stations -- an `.m3u8` manifest handed to the playlist importer used to produce
a list of two-second fragments presented to you as stations.

### One player, and every window can reach it

Quill Radio has only ever had one player. What it did not have was one
*keyboard*. Speed, skip and chapters were menu items on the main window, and a
menu accelerator only fires for the window that owns the menu bar -- so
standing in Browse Stations you could hear a podcast and be unable to change
its speed. The window you were standing in decided which half of the player
existed.

That is fixed at the root. Every transport verb is one row in one table, and
the menus, the accelerators, the Command Palette and the player's own buttons
are all built from it. Four doors, one implementation. **Ten windows** answer
to the whole transport now.

**Go to Player (Ctrl+Shift+G)** came from one question -- *"should the player
be its own window? Can we make that magical some how?"* The first answer was a
summoned panel with no window of its own; listening changed it. The Player is
now a **real window**: press Ctrl+Shift+G from anywhere and it opens -- or, if
it is already open somewhere behind you, **comes to the front**. It carries
the whole transport, what is playing, where you are in it, the speed and the
volume; it stands in the Window menu and the Ctrl+Tab rotation beside Browse
and the managers; and its readout follows changes made in any other window.
Escape closes it and focus returns to the window you came from.

**Ctrl+Shift+P opens the Command Palette from every window**, and the whole
transport is in it. Every on/off command in the palette now carries its own
state -- **"Announce Track Titles (currently On)"** -- because a palette has no
checkmark, so the entry used to read the same whichever way the switch actually
was, and you had to throw it to find out.

**Every key now says what it did.** The rule was already written down: a key
that cannot act says why, because a silent key is indistinguishable from one
that is not bound. The refusal path honoured it; the success path did not.
Play/Pause, Stop and Mute all did their job and said nothing at all in every
window but the main one. Mute was the worst of the three -- silence is what
muting is *for*, so with no word there was no way to tell muting apart from the
stream dropping out.

**And windows stay where you put them.** Browse Stations, Search Stations,
Manage Favorites and Schedule Recording were dialogs, and a dialog cannot carry
a menu bar -- so opening one made the menu bar seem to vanish, and the modal
ones locked you out of the main window entirely. They are proper **windows**
now -- each a real, independent window with its own place in the taskbar and
the Alt+Tab order, not an overlay floating glued over the main one -- each
carrying a menu bar, none holding the main window hostage. A new **Window**
menu lists everything you have open, with **Ctrl+Tab**, **Ctrl+Shift+Tab** and
**Ctrl+1** through **Ctrl+9** to move between them; moving to a window lands
you on the control you last used there. Asking for a window that is already
open brings it to the front rather than opening a second copy, and each closes
the way windows close: **Escape, Ctrl+W, Ctrl+F4, Alt+F4, or the titlebar**.
**Recordings, Downloads, Song History and the Now Playing viewer** are windows
of the same kind, so the whole app now moves under one set of window keys.

### Every menu item tells you its key

Open any menu in 3.0 and every item ends with the way to reach it from the
keyboard. Browse Stations is **Ctrl+B**, Find Stations **Ctrl+F**, Recordings
**Ctrl+Shift+R**, Go To **Ctrl+G**. All 115 items, menus and submenus alike.

This was not a polish pass. Forty-nine items had no shortcut at all, which
meant the only way to learn there was no faster route was to arrow through the
whole menu and reach the end -- a cost paid on every visit. Seven keys were
claimed by two different items, so one of each pair silently did nothing. And
two items advertised keys the toolkit was quietly discarding as unparseable,
which is the worst of the three: a menu promising a shortcut that could never
fire.

Where an item has a shortcut you can change, the menu shows **the key you
actually have bound**. A build check now fails if any menu item ships without a
working, unique key, so this stays true.

The main window's own controls carry Alt keys too -- **Alt+M** mutes, **Alt+U**
reaches the volume slider -- each using a letter the menu bar has not claimed,
with a build check refusing any that does. (The transport buttons themselves
left the main window in the surface redesign; their verbs live on the keys, the
menus, and the Player window.)

### Things that were quietly wrong, and are not now

Five worth knowing about, because every one of them was broken and not one
announced itself.

**Installing your apps in the wrong order cost you the playback engine.** Quill
Radio plays through mpv; without it the app drops to Windows Media and loses
live pause and rewind, output-device choice, Volume Boost, track titles from the
stream, stall detection, and every Ogg Vorbis, Opus and HLS station. The mpv
library and FFmpeg are 306 MB together, so they are not built into the shared
QuillVille Runtime that all seven apps use -- four of those apps never call
them, and Quill Weather's installer was once 191 MB to read out a forecast.
Each media app contributes what it needs instead.

That is a sound arrangement, and the install step did not honour it. The tools
were installed by the same instruction as the runtime itself, which is skipped
when a newer sibling app has already put a runtime on the machine. So installing
QUILL Cast -- which needs FFmpeg and not mpv -- and *then* installing Quill
Radio skipped Radio's payload entirely, and mpv never arrived. Nothing said so.
The app fell back, played most stations, and simply could not play some.

Reinstalling did not help either, though the app confidently said it would: the
reinstall met the same skip. Both halves are fixed. The tools are now laid down
unconditionally, so a machine ends up with the union of what its apps need
whoever installed first, and reinstalling really does restore them.

And for the case where reinstalling is not the answer at all -- the **Lite**
installer downloads the base runtime and carries no media tools by design --
**Help > Get mpv Playback Engine... (Ctrl+Alt+M)** simply fetches it, about
46 MB, the same checksum-pinned package the build itself uses. Audio Health has
a button for it too, next to Get FFmpeg, lit only when pressing it would change
something. It arrives with mpv's licence texts and its corresponding-source
offer, because those are part of shipping it rather than paperwork bolted on
afterwards.

**A station that hiccuped once was dead.** This came in as a report while 3.0
was being finished, and it is the most consequential fix in the release:
stations like KFI would play for about twenty seconds and then stop, or repeat
their last five seconds. iHeart serves those as HLS -- a thirty-second window
of buffered audio behind a token that expires in five seconds -- so missing a
single refill looked exactly like the stream ending, and Quill Radio said
"Stopped". Now the connection heals itself at the transport level; a genuinely
dropped station is reconnected **out loud** ("Reconnecting to KFI AM 640.
Attempt 1 of 3."); and iHeart stations are asked for their steadier progressive
stream where one exists.

**A reconnect counted its attempts out loud, to nobody.** The code composed
exactly the right sentence and wrote it into a field that nothing spoke and
nothing displayed. What a listener actually got was one sound and then up to
twenty-two seconds of silence -- indistinguishable from the app having hung.

**A recording that captured nothing said nothing.** A recording file is created
the moment recording begins, before a single second of audio arrives, so "the
file is there" never meant "something was recorded". A capture that saved
nothing is now reported as what it is, with the reason -- *"Recording of 96.5
The Fan saved nothing: the connection failed. No file was kept."* -- the empty
file removed rather than left for you to find and wonder about, and the error
sound used rather than the saved sound.

**The status line stopped saying "playing" through silence.** When a live
stream ran out of audio, the app said "Buffering..." and left its playback
state at *playing*, so the status bar and tray tooltip went on claiming
playback through dead air -- the one thing a listener can already tell is
false. Buffering is its own state now, and reconnecting reads **"Radio:
Reconnecting to KFI AM 640. Attempt 2 of 3."** rather than *connecting*, which
is what a station **you just chose** does.

Alongside those: recordings interrupted mid-capture are **stitched back into
one file** under the name you expected; a recording whose file stops growing is
noticed even when nothing reports a problem; **every destructive question now
defaults to No**, so pressing Enter reflexively no longer destroys the thing;
and deleting a row leaves your cursor on the row that took its place rather
than at the top of the list.

The forensics on all of these -- and a dozen more, including the 412 genres
Xiph was losing on every refresh -- are in the in-depth companion.

### A recording that the computer is actually awake for

This one came from a listener, not a bug report, which is the only way it could
have come. He scheduled a football pregame show for 11:00 and Quill Radio
announced the recording at 11:03. Nothing had failed. Nothing said anything was
wrong. He simply lost the first three minutes and had no way to find out why.

A schedule is a thread inside a running application, and a sleeping computer
does not run threads. Quill Radio has always kept the machine awake *while*
something is playing or recording, and did nothing at all about the quiet
stretch beforehand -- which is exactly when a machine with nothing to do
decides to sleep.

Three answers now, meant to work together. **It says so**: the scheduling
window states the requirement in a line, before you set anything, because a
requirement you only discover by losing the first three minutes of a game is
not a requirement, it is a trap. **It holds sleep off as the time approaches.**
And **it can wake the machine**, through a Windows task registered a couple of
minutes before the recording -- because no amount of asking from inside a
sleeping process will help.

Both automatic parts are separate checkboxes, both on by default, and separate
deliberately: holding sleep off is a small local thing, while waking the
machine changes how your computer behaves.

### Winamp's keys, in the Recordings player

If you came to Windows audio through Winamp, its classic-skin keys never really
left your fingers. Until now the Recordings window answered to exactly two of
them. The whole transport set is now there, on the letter keys you already
know, with no modifier: **X** play, **C** pause, **V** stop, **B** next, **Z**
previous, **R** shuffle, **S** repeat, **T** elapsed or remaining, **J** jump
to a recording by name, **Ctrl+J** jump to a time.

Two places it parts company with Winamp, both the better answer here.
**Ctrl+T stays What's Playing**, because in a radio app knowing what is on the
air is worth more than an elapsed-time toggle; the toggle is on plain **T**.
And **Up and Down still move through the list**, because the recordings list
*is* a playlist editor by any other name.

Shuffle is a fixed reorder rather than a fresh roll each time, so every
recording plays exactly once before any repeats and **Z** is the exact inverse
of **B**. If you would rather have the letters for list typeahead, a preference
turns them off.

### How Quill Radio reaches you now

Quill Radio, QUILL, Quill Weather and QUILL Audio Studio now share **one**
Python engine -- the **QuillVille Runtime** -- installed once per user and
reused by every app in the family. Install any one of them and every app you
add afterwards starts instantly. The runtime is reference-counted, so it is
removed only when the last app relying on it is uninstalled.

That unlocks two much smaller ways to get Quill Radio:

| Edition | Size | What it is |
| --- | --- | --- |
| **Companion** (new) | ~1 MB | Just the app and its docs, on the shared runtime. Offers to install the runtime once on first launch if it is not there. |
| **Lite installer** (new) | ~3 MB | Installs the app; fetches the shared runtime only if it is missing. |
| **Portable zip** | ~210 MB | Still the one for a USB stick: fully self-contained, no installation, no internet. |
| **Full installer** | ~158 MB | The recommended path: the shared runtime plus the app. |

Whenever the runtime is downloaded, the progress bar works with NVDA, JAWS and
Narrator, announcing progress as a percentage the whole way.

**And updating gives you back the edition you installed.** If you have ever
chosen Check for Updates and been handed the *portable zip* when you installed
Quill Radio properly, this is the release where that stops. Each installer now
writes down which edition it is, and an update offers that same edition back.

**Friendlier to antivirus.** The launcher is a genuine, tiny native program and
the Python it runs is the official, unmodified build -- the renamed-and-modified
`pythonw.exe` pattern that some antivirus tools flagged is completely gone. And
as of 3.0, releases are **code-signed**: the installers, the uninstallers and
the app itself carry a genuine Authenticode signature.

**A global hotkey, and a family menu.** **Ctrl+Alt+Shift+R** from inside any
program tucks Quill Radio into the tray or brings it back, without stopping the
music. If another app has already claimed that chord, Quill Radio leaves it
alone rather than fighting for it. And the **QuillVille** menu (**Alt+Q**)
lists every app in the family from inside any of them.

**Weather moved out.** The weather work that grew up in this release now lives
in **Quill Weather**, a small tray-resident app of its own that watches your
location for official alerts. Quill Radio has no Weather menu at all anymore --
one watcher, not two, and the radio opens talking about radio. What stays is
the radio part of weather: the **Weather / NOAA** branch, every NOAA Weather
Radio transmitter with an internet feed, searchable by call sign, SAME code or
"County, ST".

**An icon of its own.** Quill Radio's icon was never the problem. The problem
was that it was also Quill Inkwell's, Quill Weather's and QUILL Audio Studio's
-- byte-identical copies of one file, so four products wore one face in the
taskbar. Every app has its own now, still recognisably a set, separated by
silhouette *and* by a colour that differs in lightness as well as hue -- because
a set separated only by hue is a set some colour-blind users cannot tell apart.

**And your whole setup can follow you between computers.** **Preferences >
Data Folder...** points the shared Quill data folder at something Dropbox,
OneDrive, Google Drive or iCloud already syncs. There is no Quill account, no
API and nothing new talking to the network: Quill writes to the folder and the
sync client you already run does the carrying.

### A podcast you can look at before you decide

There is a new branch in Browse Stations called **Podcast Index**, and it does
the one thing no podcast surface in this app could do before: it lets you look
at a show without subscribing to it.

That sounds small. It is not. Until now, a show was a name and a description,
and the only way to find out what it actually published -- how long the
episodes are, how often they come, whether the last one was three years ago --
was to subscribe, go to your subscriptions, and read the list. You had to
commit in order to ask a question. If the answer was no, you unsubscribed and
the show left a mark in your library on the way out.

Open a show in this branch and its episodes are simply there. Arrow through
them. Press Enter on one and it plays. Add it to Favorites, download it, read
its transcript -- they are ordinary rows, and everything that works anywhere
else in the tree works here. Then subscribe, if you want to. Or do not, and
nothing was spent.

The rows say what they are before you open them. A show tells you who makes it,
how many episodes it has, and what it is about. It also tells you, plainly, when
the index can no longer read the feed -- which is exactly the thing you want to
know *before* subscribing to a show that will never publish again, and exactly
the thing a store listing will never say.

Three ways in:

- **Trending Now** -- what people are actually listening to today. Nothing else
  in the tree could answer that for podcasts.
- **By Category** -- the index's own hundred and twelve categories, each one a
  trending list narrowed down.
- **Search the Podcast Index...** -- answered inside the tree, like every other
  search here, so finding a show does not take the tree away from you.

**Searching for a podcast now asks both directories.** Search for a Podcast, and
Find Stations, ask Apple *and* the Podcast Index, and merge what comes back. The
index is where the independent, the self-hosted and the de-listed shows live --
the ones a store does not carry. If one directory cannot answer, the other's
results still arrive and the status line says which one was quiet.

**Subscribing from an index row is instant.** Its rows carry the feed address
itself, where a store row carries an id that has to be looked up first, so
Subscribe files the show into the library you share with QUILL Cast -- artwork,
site and all -- with nothing further to fetch.

**Nothing was asked of you to switch this on.** Quill Radio carries its own
credential for the Podcast Index, so there is no key to register for, no account
to make, and no settings page you needed to find. The credential identifies *the
app* to a directory of public information: it reads no account, it authorises
nothing on your behalf, and a search sends the words you typed and nothing else
-- not who you are, not what you are subscribed to, not what you have played. If
you would rather use a key of your own, you can, and it takes precedence.

And nothing depends on it. Turn the branch off in **Choose Browse Sources** and
podcasts work exactly as they did; Apple remains the keyless default everywhere
it was before. The Podcast Index is credited in **Help > About** -- it is an
open, independent project that exists to keep podcasting open, and this app is a
guest there.

### Radio and Cast: two apps, one library

Quill Radio plays podcasts now, and QUILL Cast is an entire podcast
application. That sounds like duplication and it is not, so here is the line
between them, plainly.

**Quill Radio is the app for finding things.** Sixty-two thousand stations,
thirty branches, live broadcast, recording on a schedule, YouTube, your
own Icecast box. Its podcast support is deliberately the *lite* half: walk
Apple's entire directory with no key and no account, subscribe, play, read a
transcript, keep the newest twenty-five episodes of a show in view. That
episode count is the **only** podcast preference Quill Radio has, and that is a
decision rather than an omission.

**QUILL Cast is the app for following things.** It is where the twenty-fifth
podcast you subscribe to stops being a pleasure and starts being a filing
problem, and it answers exactly that: an **Inbox** where new episodes wait to
be sorted with per-show filing memory, a **Play Queue** you can reorder from
the keyboard, an **acquisition policy** that keeps the newest one, three, five
or ten episodes of each show downloaded and ready without your asking,
**storage management** that shows what your library costs per show and frees
space on request, **queue expiration** so an episode that waited too long
leaves quietly and stays restorable for a week, **listening statistics** with a
retention window and CSV export, **Quick Actions** where you decide what Enter
does per content type, and **private feeds** -- a Patreon-style supporter feed
signs in per show, with the password in Windows Credential Manager and never in
an exported OPML file.

**And they are one library, not two.** Subscribe in Radio and the show is
simply *there* the next time Cast opens, artwork and site link included.
Listen to half an episode over lunch in Radio and Cast knows your real place at
its next launch: the episode stops presenting as brand new in the Inbox, and
Continue Listening picks up where you actually stopped. Neither app ever writes
the other's files -- a small handoff record carries the news -- so nothing can
be lost whichever one happens to be open.

The reason there are two apps at all is the reason this section exists: you
should not have to load a podcast environment to hear a radio station, and you
should not have to load a station directory to hear your shows. Install
whichever one matches what you came to do, and the other costs you about three
megabytes when you want it, because they already share their engine.

### What comes next

Nothing below is a promise with a date on it. It is what is being built, so
that "not mentioned" and "not coming" do not look the same here either.

**In Cast, the work is already written and waiting on its next release.** The
largest piece is **About This Episode**, which reads the rest of what a podcast
feed publishes and Cast was throwing away: who is on the episode and who makes
the show, the moments the podcast itself marked as worth hearing, a live stream
if the show is on the air right now, a smaller version of the same episode for
a metered connection, the podcasts this show recommends -- where subscribing is
a real subscribe -- and where to support the show. A tab exists only when it
has something in it, and the command speaks a one-line summary before the
window even opens, so if all you wanted was to know whether there was anything,
you never have to open it.

Alongside it: **chapters for episodes that never published any**, named by what
each section is actually *about* rather than by its first few words, with every
chapter carrying where it came from and how confident that was, so an inferred
list is a claim you can inspect rather than one you take on faith. An **Inbox
that can work the other way round** -- every show except the ones you exclude,
which is the mode people with a hundred subscriptions actually want. **Hold
Shift+Right to scan** forward at four times speed and release back to exactly
the speed you were at. And **an OPML file that opens by double-clicking it**,
because a subscription list handed over from another app should not need a file
picker inside a dialog inside a menu.

**In Quill Radio, the next milestone is one piece of work rather than four.**
Three more station catalogs -- **FMSTREAM**'s international directory, and the
**SHOUTcast** and **Icecast** webcaster directories -- plus **RadioDNS**, the
broadcast-radio standard that carries a station's real name, identifiers and
logo, all landing behind **one canonical station record**.

That last part is the whole point, and it is why these are not four separate
features. Add three directories to a browse tree and the same station arrives
three times under three slightly different names, and a listener gets to guess
which row plays. RadioDNS is what reconciles them, so one station is one row
with its provenance attached. Shipping any catalog before the reconciler would
have produced precisely the duplicate problem the reconciler exists to solve,
which is why the milestone is not finished until all of it lands together.

After that, in rough order: deeper **NOAA Weather Radio and NWS** directory
work, a **RepeaterBook** partnership for amateur-radio metadata, a prototype
for **public SDR receivers** you can listen through, and a submission directory
for **radio-reading services**, which is the one on the list this project
considers mission-critical rather than merely valuable.

---

## Part Three: When something goes wrong, or you change your mind

Everything above is about what the app can do. This part is about the moments
it used to handle badly -- and none of them are features anybody goes looking
for. Each is something Quill Radio owed you and was quietly not paying.

### You can take it back

Press **Ctrl+Z**.

Unsubscribe, Remove All Downloads, Delete Recording, Mark All as Played --
the last one comes back, and the app says what came back: *"Undid Unsubscribe.
Brought back The Daily, with 412 episodes and 3 downloaded files."*

The alternative, and the thing this deliberately is not, was asking you first
every single time. A confirmation prompt costs a keystroke and a sentence on
every one of the nine hundred occasions you meant it, and it still cannot help
you on the one occasion that matters -- because on that occasion you read the
question, thought about a different row, and pressed Yes. The prompt was never
protecting you from a slip of the finger; it was protecting you from a slip of
attention, which is exactly the thing it cannot see.

Three things worth knowing.

**It is one step, not a stack.** Press Ctrl+Z twice and the second press says
"Nothing to undo" rather than quietly rewinding something older that you had
forgotten about. If you have to count how many times to press it, you have
been handed a puzzle rather than an undo.

**Deleted files genuinely come back.** A file Quill Radio deletes on your
behalf is moved aside rather than unlinked, so undoing a Delete Recording
restores the recording itself and not merely its name in a list. What was held
is released for good when you do the next destructive thing -- which is
precisely what makes a single step safe to offer without asking first.

**It tells you what it cannot bring back.** Unsubscribing from a private feed
deletes the password stored for it, deliberately, so no orphaned secret is
left behind. The undo restores the subscription and says the password has to
be entered again. That sentence is in the offer, not in a support email.

Every action that can be undone ends its own announcement with "Ctrl+Z undoes
this", so you never have to remember which ones were on the list.

### Recent Problems

**Help > Recent Problems...** (Ctrl+Alt+Shift+P).

Quill Radio talks. A feed fails, a download dies, a stream drops and cannot be
reconnected, and it tells you -- once, at the moment it happens. That is right
almost always, and completely wrong the one time the sentence went past while
you were in another window, or asleep, or making tea.

This was the one place this app was not built the way the rest of it is.
Somebody who can see the screen still has a list to scroll back through.
Somebody listening had nothing at all: the announcement had been made, so as
far as the app was concerned the job was done.

Now every failure worth a second look is written down as well as spoken: what
failed, why, and when, newest first. **Retry** tries the highlighted row again
-- plays the station, re-queues the download. **Copy All** takes the list as
text, which is the thing to paste into a bug report; it carries addresses and
error messages, never passwords. **Clear List** empties it, and does not fix
anything or stop the same problem being recorded again next time.

A feed that has failed on each of the last six checks reads as one row with a
fresh time rather than six identical rows, so a feed checked every fifteen
minutes cannot bury everything else. A *different* reason gets its own row,
because "404 Not Found" and "timed out" are not the same news.

Nothing in this list leaves your computer.

### Quiet hours

**Help > Quiet Hours...** (Ctrl+Alt+Shift+Z). 22:00 to 07:00 by default, and a
window may cross midnight.

Inside it, Quill Radio stops speaking **on its own**: the heartbeat of a feed
check, the announcement that new episodes arrived.

Three things it does not mean, all of which the window says out loud, because
the name invites exactly these misreadings:

- **Nothing stops happening.** Feeds are still checked. Downloads still run.
  Recordings still record. Only the announcements wait.
- **Anything you press a key for still answers.** Press Play at three in the
  morning and you hear what is playing. Quiet hours never silence a reply to
  something you asked for -- they hold back only the speech nobody asked for.
  That is not a detail of the implementation, it is the line the whole feature
  is built around, and it is why every announcement had to opt in by name
  rather than everything being switched off at a single point.
- **Failures always speak.** A recording that stopped at 3 a.m. is precisely
  what somebody sets an alarm-clock radio for.

One override, for the one thing people legitimately want through a quiet
window: reminders can be let through anyway.

The window is shared with QUILL Cast and the rest of the family, so you set it
once.

### Move your setup to another machine

**Help > Export My Setup...** (Ctrl+Alt+Shift+X) writes one file. **Help >
Import My Setup...** (Ctrl+Alt+Shift+N) reads it on the other machine.

Inside it: your favorite stations and the folders you filed them into, your
saved places, your settings, your Go To list in the order you put it, your own
streaming servers, your scheduled recordings, your recording settings, your
YouTube rows and channels, your bookmarks, and any keys you rebound.

An OPML export has always moved your podcast subscriptions and nothing else --
which is to say it moved the part that was easy to standardise and left behind
the part you had actually built.

The file is an ordinary ZIP with a readable manifest, deliberately: you should
be able to see what you are carrying, and somebody who no longer runs this
software should still be able to get their subscription list out of it. It
carries a **declared list** of files rather than whatever happens to be in the
data folder, because a sweep of a folder eventually carries a cache, a lock
file, or a credential nobody meant to move.

**Passwords are not in it.** Private-feed sign-ins, server credentials and
unlock codes stay on the machine that holds them. The confirmation says so
before it does anything, rather than leaving you to find out when a feed stops
working.

Importing **replaces** what is on the other machine rather than merging with
it, and says so first. Merging two libraries is a different job with different
questions, and pretending this one does it would be the expensive kind of
kindness.

### Your place follows you into QUILL Cast, and back

Both apps can play the same subscribed episode. Until now, half an episode
heard here reached Cast at Cast's next launch -- the one moment you are least
likely to be mid-episode -- and nothing came back the other way at all.

They now share one place per episode on this computer, written **when you
pause** as well as when you stop. Quill Radio never wrote a position on pause
at all, so what it reported was always from whenever you had last pressed
Stop.

Open an episode you were part-way through in the other app and it picks up
where you left off, and says so: *"Picking up where you left off in QUILL
Cast, at 1 hour 2 minutes 3 seconds."* Resuming where you left off in *this*
app stays silent, because that is ordinary and does not need narrating; it is
the cross-app jump that is surprising, and a jump nobody explained is
indistinguishable from a bug.

The **later** decision wins, not the furthest through the episode. If you
skipped to the outro to check something and then went back to the middle, the
middle is where you are. An app that dragged you forward again on the grounds
that it was further in would be overruling you with arithmetic.

### Skip Silence, and a speed that sticks

Two things the playback engine could always do, and Quill Radio never offered
outside podcasts.

**Skip Silence** (Playback > Skip Silence, Ctrl+Shift+9) shortens the long
pauses in a recording, a YouTube row or a podcast episode as it plays. It
takes effect on what is already playing, with no interruption and without
losing your place. On live radio it says plainly that it will do nothing -- a
broadcast plays at broadcast speed and its pauses have already gone out --
rather than appearing to work and not working.

**Play Faster is remembered.** A speed chosen during a recording applies to
recordings; one chosen on a YouTube row applies to YouTube rows. Per kind
rather than per row, because what somebody means by "1.5x for recordings" is
every recording, and asking them to set it again for each captured hour would
be the same feature with the cost moved onto them.

### Smaller things that were quietly wrong

**A dimmed menu item now tells you why.** Quill Radio dims a great deal on
purpose -- Mark All as Played with nothing unheard is a *state* of a verb that
row genuinely owns, and an item that vanished would read as the feature coming
and going. But a screen reader says "dimmed" and stops. Each now carries its
reason: *"Remove All Downloads: nothing is downloaded for this show."* The
command palette says it too, instead of a bare "(unavailable)".

**Add to Favorites stopped lying.** The favorites store answered the same
thing whether or not it had added anything, so adding a station you already
had announced "Added WQXR to Favorites" over nothing happening. It now says
you already have it -- and moves the cursor to the one you have, which is the
question you were actually asking, since the reason anybody adds a thing twice
is that they could not find the first one.

**Download All counts.** It queued the lot and said whatever the queue said
next, so a folder of forty chapters with thirty-nine already on disk reported
the same thing as a folder of forty new ones. It now says how many were
eligible, how many started and how many it skipped -- which required teaching
it, for the first time, how to tell whether a row was already here.

**Find in this folder searches descriptions.** Ctrl+F matched a row's name
only. On a podcast show's branch that is episode search, and a show that
numbers its episodes and puts the subject in its show notes -- most interview
podcasts -- was a show you could not search at all.

## Part Four: Three more directories, and the day they were tested

*Added late in 3.0, after the notes above were written -- which is why they read
as a separate chapter rather than being folded through the rest.*

### Three new places to find a station

Quill Radio already browsed more of the internet's radio than anything else
built for a screen reader. What it did not have was the largest index of small,
independent broadcasters anywhere, the second-largest, or a proper connection to
one of the few stations that publishes lossless audio. It has all three now, and
none of them needs a key, an account, or a registration.

#### SHOUTcast

Quill Radio has understood a SHOUTcast *server* for years — it reads their
status pages to tell you what is playing. It has never had SHOUTcast's
*directory*, which is a different and much larger thing: tens of thousands of
stations, most of them run by people rather than companies.

It arrives as one branch with two ways in.

**Top 500 (most listeners right now)** is pinned at the top of it, and it is the
closest thing in this app to *what is the internet actually listening to at this
moment*. Not votes cast over years. Not a chart somebody curated last spring.
The 500 stations with the most people listening to them right now, most first.

**Then 313 genres**, from Adult Contemporary to Zouk. Two things are worth
knowing about them and both are said out loud rather than left to be discovered:
SHOUTcast returns at most 500 stations for a genre however many it holds, so a
big genre is a good sample rather than the whole thing; and every list arrives
**sorted by live listeners**, because a SHOUTcast genre page is mostly stations
nobody is listening to and putting those first would waste your time. In one
measurement of a Jazz page, 39 of the 500 had an audience at all.

Each station also carries what it was playing when the list was fetched, which
is often the quickest way to tell two similarly-named stations apart — and it is
worded so it is never mistaken for live now-playing, which arrives from the
stream itself once you press Enter.

#### Live365

About 5,500 independent stations, arranged A to Z. Quill Radio could already
play a Live365 link somebody handed it; it could not *find* one, because
Live365's station directory needs an account we will not ask you for. Its
public sitemap needs nothing at all — the same route this app already uses for
iHeart — so that is what this reads: one request a day, every station in it.

#### Radio Paradise, properly

It used to be a name search against a community directory, which returned
whatever a stranger happened to have registered, at whatever bitrate they
registered it. It is now the station's own channel list — The Main Mix, Mellow
Mix, RockIt!, The Globe, Beyond, Serenity, KFAT and Radio 2050 — **each at every
quality it offers**. That runs from 32 kbps AAC+ for a phone tether up to
**lossless FLAC**, which nothing else in the tree offers. Every one of those
addresses was played before it was written down; Serenity offers only two of the
six, so only two are shown, because a row that will not play is worse than a row
that is not there.

### Live listeners, as a fact of their own

Community votes tell you a station was well-liked, at some point, by people who
bothered to vote. They do not tell you it is on the air. Where a directory
actually measures its audience, that number now travels with the station and
reads in the details panel as "Live listeners: 8,281" — kept deliberately apart
from votes, because reading one as the other is how a list fills up with
stations that went off the air in 2019.

### A tree that tells you when a source is having a bad day

"Could not be reached", three times, in identical words, reads as three
unrelated hiccups. From the second failure in a row a source now says which it
is: "It has failed 3 times in a row — the directory itself may be down. You can
hide it in Browse Sources."

Quill Radio will not switch a source off for you. A branch that quietly
disappeared would be a worse failure than the outage it was hiding, and
directories recover. The tally is forgotten when you close the app.

### Search that stops being slow, and says so while it works

*(Two passes: the fan-out, then the thing that was actually slow.)*

**Search All Sources** asked sixteen directories through six workers, which
meant three waves of the slowest service back to back. Every source is now asked
at the same moment.

That was not the whole of it. Two directories — TuneIn and iHeart — need a
separate request for *each result they find*, to turn a listing into an address
you can play, and they were making those requests one after another: ten of them
end to end for a single TuneIn search. They now go out together, which is the
difference between a search that takes ten seconds and one that takes about one.
Searching SHOUTcast from the tree now costs a single request, because its rows
work out their address when you press Enter on one.

With the slow shapes gone, the ceiling on the whole search came down to eight
seconds — after which any straggler is **named** ("Internet Archive did not
answer within 8 seconds") rather than quietly left out, so a short list never
passes itself off as a complete one.

While it runs it now tells you so, after about four seconds and then
periodically, because a cross-source search is as slow as the slowest service in
it and nothing on screen changes while it happens.

And when you are done with the answer, **Delete** on the Search Results branch
closes it — or **Close Search Results** on its context menu. It is the one
Delete in the tree that asks nothing, because the branch owns nothing: your
query is still in the Find box.

### The Find box meets you where you are

Standing on **Search All Sources...** and reaching for the Find box — Ctrl+F, or
one Shift+Tab — used to get you "type something to find in this folder", about a
row that is not a folder. Type there now and press Enter and it searches
everything for what you typed, with no second prompt to answer. The same is true
while you are standing in the results: typing a new query starts a new search.

Everywhere else the Find box is exactly what it was, and filters the branch you
are in.

### Sorting that reads like a person wrote it

A folder that listed "ACB Media 1, ACB Media 10, ACB Media 2" now lists 1, 2, 3
and on to 10. Numbers inside a name are compared as numbers — in the browse
tree, the A-Z groups, the new Live365 directory and your favorites.

Nothing was renamed to achieve it. Padding the stations out to "ACB Media 01"
would have been wrong in the details panel, wrong read aloud, wrong in an export
and wrong the moment you searched for the name you actually know. The display
name belongs to the broadcaster; the ordering belongs to us.

### Smaller things, and one confession

- **All three new directories are searchable**, from Find Stations *and* from
  the tree's Search All Sources, each with its own on/off switch — and a source
  that is off is never contacted rather than having its results discarded.
- **A source you switch on appears immediately.** Choosing Browse Sources used
  to write the setting and leave an open Browse Stations window showing the old
  list until the app restarted. It now rebuilds as the dialog closes, and says
  "Browse Stations has been updated."
- **A source added in a new version now reaches people who already made a
  choice.** A stored list of sources cannot name one that did not exist when it
  was saved, so anybody who had ever opened either chooser would never have seen
  these three at all. Fixed for browse sources and — for the first time — for
  search sources.
- **Four more playlist shapes** are understood when one is handed to Quill
  Radio: ASF redirectors, saved URL shortcuts from Windows and from Linux
  desktops, Winamp `.b4s`, and Windows Media `.wpl`.
- **The confession.** SHOUTcast stations did not play at first. What that
  directory publishes is a playlist holding the real address, not the address
  itself, and the first version handed the playlist to the player. It was caught
  the same afternoon on a station with 293 people listening to it. Stations are
  now resolved the moment you press Enter — one request on the station you
  chose, rather than five hundred for a page you are only reading — and a
  station that cannot be resolved is left out rather than offered and then
  failing.

### Television

The biggest addition in this part, and the shortest to explain, because it
behaves exactly like everything else. **Television (iptv.org)** -- just above
YouTube in Browse Stations -- is about 9,300 playable TV channels from the
open iptv.org community catalog, browsable by country and by category, and for
countries with local broadcasting, by **state and city**: the United States
opens into Nationwide plus fifty-odd states, each carrying its own and its
cities' channels, city named on the row. Search understands television
everywhere search exists, and it understands **places**: a five-digit ZIP code
answers with that state's channels, because 66044 means "TV around Lawrence",
not "channels containing 66044". Press Enter and the video plays with the
captions and audio-track handling every stream already gets.

The honest edges are documented rather than papered over. Channels flagged
adult are absent -- this is a family of applications, and the catalog carries
the flag precisely so a client can make that choice. "Which channels can my
antenna receive?" opens antennaweb.org in your browser, because that tool has
no public interface and Quill Radio does not scrape. And a **TV guide** is one
file away: drop an XMLTV file named `tv_guide.xml` into your data folder and
every covered channel says what is on now and next -- read locally, never
fetched, gone the moment you delete it. The channel list refreshes weekly (it
is the heaviest catalog in the app) with an update-now action on the branch.

### Quillins can bring their own station sources

Until now an installed Quillin could add stations to *search results* and
nothing else. A Quillin that declares the new browse trio -- categories,
stations, and an optional play-time resolve step -- is now a **whole source**:
a Quillin Sources branch appears when one is installed (and is simply absent
otherwise), its stations play and favourite like any built-in source, and a
row may carry an opaque key instead of an address, resolved only at the moment
of playback, so a stream a provider must not cache never lands in a favourites
file or an export. Any network a provider uses runs through the Quillin host's
hardened fetch, bounded by the allowlist its own manifest declares. The
bundled Radio Community Directory sample demonstrates the whole shape.

### The Station menu, wherever you are standing

Quill Radio's windows are peers, and until now each one's menu bar held exactly
two menus: its own, and Window. So Alt+S -- the Station menu -- worked in the
main window and nowhere else, which is a strange rule to have to learn and an
impossible one to discover. It was reported twice in one day, which is how you
know it is the model and not a missing item.

Every radio window now carries a **Station** menu too: Browse Stations, Search
Stations, Manage Favorites, Recordings, and Preferences, each showing the key
you actually have bound, each running the exact same code the main window runs.
A window never lists itself, and never takes a key its own controls already
use -- inside Browse Stations, Ctrl+F still goes to the Find box.

### Search, the fourth pass: instant repeats and a warm start

Three passes made the search concurrent, resolved results in parallel, and put
local answers on screen in under a second. Two costs remained, and both are now
gone. Searching the same thing twice -- checking whether a station came back,
re-finding the row you closed -- used to pay for the whole fan-out again; the
finished answer is now remembered for ten minutes and renders *instantly*,
while a fresh search runs quietly behind it and takes its place. And the first
search of a run used to pay to fill the very caches it answers from; opening
Browse Stations now fills them in the background before you have typed
anything. A source you switched off is never contacted -- not even by the
warm-up -- and Safe Mode skips it entirely.

### Sources with opinions of their own

Two of the new directories took an option, and the way they took it matters
more than the options. **Source Options...** on a source's context menu asks
Radio Paradise which quality Enter should land on (from 32 kbps for a phone
tether to lossless FLAC -- nothing is hidden, the rest stay one arrow key
away), and asks SHOUTcast whether to list everything or only stations with
listeners right now. Under it is a declaration system: a source states its
options as data and the app renders them with the platform's own dialogs, so
the next source that wants a setting writes a tuple, not a dialog, and a
screen reader meets a control it already knows.

### Alt+S, the real story

Adding the Station menu to every window turned out to be half the fix. The
other half was stranger: a *label* was stealing the key. The browse tree's
caption -- "&Stations (expand a source to browse it):" -- claimed Alt+S, and
on Windows a control label's mnemonic silently outranks the menu bar's, so
Alt+S moved focus to the tree and the menu never opened. Once found, the class
turned out to be everywhere: seventeen labels across seven windows were
disarming the very menus their own windows carry -- the Recordings window's
list label ate its own Recordings menu. Every label has moved to a free letter
(the browse tree is now **Alt+T**, which is the fair trade: Alt+T jumps to the
tree, Alt+S opens Station), and a new test forbids any label from claiming a
letter its window's menu bar owns, so the class is closed, not just the cases.

### Every app, every menu item, a key

The rule that every enabled menu item shows its keyboard route has been
enforced for Quill Radio since 3.0 -- by a gate that, it turns out, only ever
walked Quill Radio. A family-wide sweep found **116 menu-bar items with no
accelerator**: 46 in QUILL Cast, 30 in Audio Studio, 18 in Media Player, ten
each in Inkwell and Weather, six in Converter. Every one now carries a unique
key, chosen against each app's existing claims, and a family-wide gate keeps
the next app honest. Search also got quicker at iHeart specifically: it now
uses iHeart's own relevance search -- two requests, ranked results, streams
included -- instead of filtering a downloaded index and fetching a page per
match.

### Two menus that never opened

**Quillins** asked for Alt+Q. So did **QuillVille**, sitting beside it on the
same bar. Only one of them can have it, so one of them silently did nothing --
for as long as both have been there. Quillins is **Alt+N** now. (QUILL Audio
Studio had the same fault: Voices and View both asked for Alt+V. Voices is
Alt+I.)

Quill Radio has checked since 3.0 that every *item* in a menu shows a key and
that no two items share one. It had never checked the **menus themselves**,
which is the rung you need first: a menu you cannot open is a menu whose items'
keys do not matter. That check now exists for every menu bar in the family, so
neither fault can come back.

And the menus are now *on* the Keyboard Shortcuts Sheet (Ctrl+Alt+Shift+K), at
the top, with the key that opens each one — read off the bar in front of you, so
it is right in whichever window you are standing in.

### Where each window's menu is

Quill Radio's windows are peers, not dialogs, and each carries its own single
menu — so the letter that opens one depends on where you are standing. Alt+S is
**Station** in the main window, **Search** in Find Stations, and nothing at all
in Browse Stations, which is Alt+B. Every one of them is now listed in the
Keyboard Shortcuts Sheet (Ctrl+Alt+Shift+K) under the window it works in, and in
the user guide.

## The rest

### Two things the ACB schedule was getting wrong

Both were found on 2026-08-24 by reading the live feed rather than by a test,
and both are the kind that do not announce themselves.

**Every programme was five hours early.** ACB writes its calendar in US
Central time and says so in the feed; Quill Radio read those times as though
they were UTC and then converted them to your clock. Everything moved by the
same amount, so the schedule still looked like a schedule -- there was nothing
on screen to compare it against. Times are now read in the zone they were
written in. If you had learned to mentally add five hours, you can stop.

**A repeating programme could vanish.** ACB published their first genuinely
recurring entry this month, and its repeat rule ends before the event it is
attached to. Read strictly, that produces no occurrences at all and the
programme simply is not in the schedule -- no error, no gap, nothing to
notice. The first occurrence is now always shown, which is what every other
calendar does with the same entry. A programme you deliberately cancelled
stays cancelled, and a series that genuinely finished months ago stays gone.

**The Command Palette key worked in neither app.** Ctrl+Shift+P is installed
on every window, and it opened nothing anywhere -- silently, which is why it
went unreported: a key that does nothing is indistinguishable from a key
nobody bound. It opens the palette now, from any window.

### What is not in 3.0, and why saying so matters

"Not mentioned" and "not built" look identical from the outside, so here is the
rest.

**Live streams still have no transcript.** The reader works on a finished
video's captions and on a published transcript, both of which exist as a
document before you open them. A live broadcast has no such document.

**Quill Radio itself has no sync setup for playback positions.** Where you got
to in a recording is remembered on the computer you were using. The Data Folder
above carries your settings and favorites between machines; the full QUILL
application can carry playback positions too.

**Adding a YouTube playlist is an import, not a subscription or a play queue.**
The videos become ordinary favorites. Nothing plays through them in order and
nothing re-checks the playlist later -- run the command again to collect what
was added since, and anything already in your favorites is skipped rather than
duplicated.

None of this is blocked; it is listed because you should not have to guess.

## Part Five: The app teaches itself

There is one more thing in 3.0, and it is the one that changes what the app is
for somebody on their first day.

**Help > Tutorials... (Ctrl+Alt+F1)** opens 36 guided tutorials -- 251 steps,
six tracks, about three and a half hours of material if you worked through
every one -- covering every feature Quill Radio has, in the order somebody
would actually learn it.

They are not a second copy of the user guide. A guide answers "what does this
do". It cannot answer "what do I do now", because a document cannot see what
you have already done. This window can.

### You open it from wherever you are stuck

The Tutorials window opens on a contents tree: six tracks, each holding its
lessons, each row saying how many steps it has, roughly how long it takes, and
whether you have finished it. A filter box sits above it. Type a word and the
list narrows -- every word you type has to appear somewhere in a tutorial, so
"record tuesday" finds the scheduling lesson without your knowing which field
holds which word.

And type **here** and the list narrows to the tutorials about *the window you
came from*. Open Tutorials while standing in Browse Stations and the window
says so as it opens -- "4 tutorials here are about Browse Stations. Type 'here'
to see just those." -- because that is a thing only this window knows and the
screen reader will never say it for us.

### A lesson is one step at a time

Press Enter on a tutorial and you get one step in a read-only field you can
arrow through, review a word at a time, and copy from. The step says four
things:

- **what to do**, in a short paragraph that also says *why* -- a tutorial that
  lists keystrokes is a keyboard reference with extra words, and this app
  already has one of those;
- **the keys**, on their own line;
- **what you should hear** when it worked, which is how a screen-reader user
  checks a step rather than looking for a green tick;
- and, where there is one, **the thing worth knowing** -- the setting that
  changes it, the mistake everybody makes once, the reason it is like that.

### The keys are your keys

A step does not carry a key in its text. It names the **command** it is about,
and the key is rendered at the moment the step is drawn, from your own keymap.
Rebind Browse Stations in the Keyboard Manager and every tutorial that mentions
it says *your* key from then on.

This is the same rule that governs the Keyboard Shortcuts Sheet, and for the
same reason: a second list of keys, maintained beside the first, is a list that
is wrong by the next release. The tutorials cannot go stale about keys because
they never knew any.

### Try it does the step

Any step that names a command carries a **Try it** button, and it runs exactly
what the key would have run. So a lesson can open Browse Stations for you and
then talk you through what you are now standing in -- which is a different
experience from a document telling you to go and open something.

Where a step is about arrowing a tree or pressing Escape, there is no command
to run and the button is dimmed. Nothing pretends.

### Follow me is the part worth the whole feature

Tick **Follow me** (it is on to begin with) and the lesson watches the app
while you work. Once a second it asks a question the step declared -- *is
something playing? did your favorites grow? is Browse Stations open?* -- and
when the answer changes it says what it noticed and reads you the next step:

> Done: something is playing now.
>
> Play your first station -- step 6 of 8: Set the volume without leaving the
> tree...

Four things about that, each of them deliberate:

- **It watches state, not keystrokes.** Pressing the key, using the menu,
  pressing the status bar's Play cell, or asking the Command Palette all count
  equally, because all four did the thing. A watcher that waited for one route
  would be teaching the route rather than the thing.
- **It compares against where you started.** "Add a favorite" is satisfied by
  your favorites growing by one, not by your having forty already -- otherwise
  the step would either pass instantly for an established listener or never
  pass at all.
- **It never guesses.** Anything it cannot read answers "cannot tell", which
  the window treats exactly like a step with no check on it.
- **It is a courtesy, not a gate.** Nothing is graded, nothing is blocked,
  there is no score and no streak, and every step still has **Next**. A check
  that never comes true costs you one keypress.

### It is a window, not a wizard

The Tutorials window is a **peer window**, like Browse Stations and the Player.
It stands in the taskbar, in the Window menu, and in the Ctrl+Tab rotation. So
the way a lesson is meant to be used is: leave it open, Ctrl+Tab into the app,
do the step there, and hear the lesson move on behind you.

A modal wizard could not do that. It would own the keyboard for the whole
lesson, which is precisely the wrong shape for teaching somebody to use the
thing underneath it.

### Your place is kept

Close a lesson half way through and it opens there again. Finishing one is
remembered *separately* from where you are in it, so re-reading something you
have done does not throw away the fact that you did it. The contents rows say
which is which -- "finished", or "you stopped at step 4".

**Forget my progress** clears the lot, asks first, and changes nothing else.
There is no percentage anywhere and no completion badge: nobody opened a radio
app to be scored. Nothing about your progress leaves this computer.

### Reading, rather than doing

**Read it all** shows a whole tutorial as one page of text, for when you would
rather read than be walked. And **The whole book as a document** opens all 36
tutorials as one page in your browser, for reading straight through or
printing -- generated from the same lessons the window teaches from, so the
two cannot disagree. It ships as `tutorials` in this same `docs` folder. (The
document states the keys Quill Radio ships with. Only the window can know the
ones you rebound.)

### What is in the 36

The tracks are not categories. Each is a claim about what you can do by the end
of it.

**Your first hour** (5 tutorials, ~23 minutes) -- play your first station; keep
it and find it tomorrow; the player follows you; do anything by name; getting
unstuck. Somebody who works straight down this track finishes with a station
playing, a favorite under a name they chose, the transport keys in their
fingers, and four separate ways out of anywhere they get stuck.

**Finding something to listen to** (6, ~38 minutes) -- wandering the browse
tree; searching every directory at once; the field-based search and its
recents; stations no directory lists (a pasted stream, a scanned website, a
whole Icecast server, an imported playlist); the catalog on your own disk and
why browsing works on a train; and what to do when a station will not play.

**Making it yours** (6, ~36 minutes) -- folders and an order of your own; the
ten quick-play slots and what the main window shows; deciding what a row says
and what Enter does (Choose Columns and Quick Actions, both of which are speech
settings wearing a list setting's clothes); making the keys yours, including
system-wide hotkeys; the six settings actually worth changing; and Quillins.

**Recording** (5, ~33 minutes) -- record what is on now; book a show that has
not started yet, including the time-zone trap and the "Add Schedule is the last
button, not the first" rule; several stations at once and lossless raw capture;
living in the Recordings list with its dozen Winamp keys; and what happens when
a recording breaks -- part files, stitching, stalls, crash-resume, and which
failures are worth retrying.

**More than radio** (8, ~54 minutes) -- following a podcast and where the line
with QUILL Cast falls; audiobooks, archives and free music, including exactly
what each source will and will not let you keep; YouTube with no account
anywhere, and its honest limits; television and your own XMLTV guide; the ACB
Media schedule, reminders and Upcoming; NOAA Weather Radio; Community Picks and
suggesting one; and Spotify, with the free-versus-Premium question answered
before you spend ten minutes on setup.

**Living with it** (6, ~36 minutes) -- what was that song; keeping a moment and
moving by chapter; sleeping, waking, quiet hours and reminders; how much you
actually listened; shaping the sound (per-station volume, boost, EQ, pausing
live radio, a speed that sticks); and backing it up, moving it, updating it,
and what to do on the day something is genuinely wrong.

### One key moved to make room

**Product Requirements... moved from Ctrl+Alt+F1 to Alt+Shift+F1.** The F1
family -- F1 for the control you are on, Ctrl+F1 for the guide, Shift+F1 and
Ctrl+Shift+F1 for these notes and their companion, Alt+F1 for About -- is
ordered by how often somebody reaches for a door. A new listener reaches for a
tutorial far more often than anybody reaches for the product requirements, so
the tutorials take the shorter chord and the PRD moves out one notch. (The
obvious next chord along, Ctrl+Alt+Shift+F1, was not available: it belongs to a
QuillVille app launcher.)

If you had the old key in your fingers, that is the one thing here that will
surprise you.

### What it costs

Nothing at runtime. The lessons are ordinary data compiled into the app, the
watcher is one timer that reads a handful of values while a lesson is open, and
the whole feature is inert when the window is shut.

### Compatibility

Nothing in this release changes where your favorites, history, recordings or
settings are stored, and nothing needs migrating. Every new branch can be
ignored entirely; if you never open Browse Stations, Quill Radio 3.0 behaves
exactly as the version you are coming from did, minus the faults above.

Safe Mode continues to disable every network source and to say so per branch,
while Favorites, ACB Media, NFB Radio and the Networks catalogue keep working
offline as before.

### The long version

Quite a lot of 3.0 has a story underneath it -- why the YouTube described-audio
tracks took a second request to reach, why two Explore axes were removed rather
than shipped, why a folder full of Xiph genres was a different size on every
refresh, and how the whole browse tree was rebuilt so that the next source
costs an afternoon rather than a fortnight.

All of it is in **`release-notes-3.0-in-depth`**, which ships in this same
`docs` folder. Nothing in it is required reading. It is there because the
reasoning behind a decision is worth as much as the decision, and because
"we fixed some bugs" is not a sentence this project wants to write.

### Where the notes for 2.0 and 2.1 live

The 2.0 and 2.1 releases -- recordings you can trust, iHeart and TuneIn in the
search, weather radio and radio reading services -- have their own document,
`release-notes-2.0`, which ships in the `docs` folder beside this one.
