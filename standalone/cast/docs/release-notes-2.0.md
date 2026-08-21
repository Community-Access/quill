# QUILL Cast 2.0 -- Release Notes

QUILL Cast 1.1 made the app do things without being asked. 2.0 is about the
places it could not reach: **another directory**, **another device**, **another
app**, and the episodes whose publishers never wrote a chapter list.

Two of those are new kinds of thing for Cast entirely. It has never before been
able to hand anything to another program, and it has never before known where
you got to on a machine that is not this one.

---

## Your place follows you, and not only between QUILL machines

Cast has carried your listening position between two copies of itself for a
while, encrypted, through a folder you already sync. That works, and it will
only ever work QUILL-to-QUILL.

**Listening Places** is the other half: a small, published, plain-text format
that any podcast app can read and write, in the same folder. Turn on **a plain
file other apps can read** in *Carry My Place Between Machines...*, and Cast
keeps one file up to date with where you are in every episode -- and reads
whatever the other apps have left there.

There is no account, no server, and no signup. You pick a folder inside
Dropbox, OneDrive, Google Drive, iCloud Drive, Nextcloud, Syncthing, or a
network share, and the cloud provider you already pay for does the syncing.
QUILL runs nothing and holds nobody's listening history.

Four decisions in that design are worth knowing about, because each of them
rules out a specific way this could have gone wrong.

**Every device writes exactly one file and reads everyone else's.** Cloud
drives resolve two devices editing the same file by leaving `positions (Jeff's
conflicted copy).json` lying around, which is the single worst failure
available here. If no two devices ever write the same file, that cannot happen
-- and it scales past two devices for nothing: phone, laptop and desktop each
drop one file, and every device merges across all of them.

**The most recent position wins, not the furthest one.** If you jump back
twenty minutes to hear something again and then open the episode on the laptop,
"furthest" is exactly the wrong answer.

**Reading happens at launch and when you press Sync Now. Never otherwise.** Not
on a timer, not when the window gains focus. If a read landed mid-session and
found that another device had moved you to 52 minutes in the episode you are
listening to at 40, every available behaviour would be bad -- and moving the
playhead under somebody with no visual cue that it happened is the worst of
them. At launch nothing is playing, so there is nothing to disturb. The cost is
that a change made elsewhere while Cast is open does not appear until next
launch; the promise being kept is that your place is right when you sit down.

**Nothing in the folder says what you listen to.** Every episode is identified
by a hash of its feed's own GUID, so somebody with access to the folder learns
how many things you listen to and roughly when, and nothing about what. Episode
names are a *separate* switch, on by default because a message that says "you
and your phone disagree about Episode 214" is worth far more than one that
reads out a hash -- and off for anybody who would rather the folder learned
less.

The format is written down in `docs/engineering/listening-places-spec.md`, with
JSON conformance fixtures both implementations test against, so two apps cannot
quietly drift into disagreeing about somebody's data.

## Share the moment, not the file

Cast could copy an episode's audio address and save its audio to a file.
Neither of those is what somebody means when they say *listen to this bit*.

**Share This Moment** (any episode's menu) copies two things at once: a link
that reopens the episode at the second you shared it from, and a plain English
sentence saying the same thing -- "Blind Abilities, Episode 214, at 41 minutes
12 seconds". The sentence is not an afterthought. A link nobody can open is
worse than a sentence anybody can paste, and the person you are sending it to
very often does not have QUILL Cast at all. The sentence works in an email, in
a text message, and read down the phone.

The installer registers `quill-cast://` so a link opens the app at the right
place. Opening one is treated as what it is -- somebody else's input -- so it
resolves to a feed address and an episode GUID, both of which are looked up in
the library **you already subscribe to**. A link for a podcast you do not
follow says so and does nothing. Cast never fetches a web address because a
link asked it to, and never adds a subscription because a link asked it to.

## A second podcast directory

Add Podcast has searched Apple's directory and nothing else. Apple's is a good
default -- free, keyless, and it indexes very nearly everything -- but it knows
nothing about the Podcasting 2.0 tags Cast has built a great deal on: chapter
documents, transcripts, marked moments, credits, funding.

**Podcast Index** does, because it is the index those tags were defined for.
Add Podcast now has a **Directory** picker: iTunes, Podcast Index, or both.
Searching both merges the results by feed address and says where they came from
-- "12 results: 9 from iTunes, 3 from Podcast Index" -- and a directory that
fails does not fail the search: you get the results that did arrive, and a
sentence about the one that did not.

Podcast Index needs a free key, which is why iTunes stays the default and why
the option is simply absent until you add one (**Subscriptions > Podcast Index
Credentials...**). The key and secret go into Windows' own credential store,
never into a settings file, and they are scrubbed out of crash reports.

## Look before you subscribe

A search result is a title. Subscribing to a title is how you end up
unsubscribing from a title.

**Preview** (and Enter on a result, which now previews rather than subscribing)
opens the podcast read-only first: what it is, who makes it, how many episodes,
its own description as text you can arrow through, and its ten most recent
episode titles with dates. Between them those answer *is this the show I meant,
is it still going, and is it in my language*. Subscribe is right there when the
answer is yes.

## Folders you can listen from

Cast has had a folder tree for a long time and has never had a single action
*on* a folder. Forty shows filed into "News" made the list tidier and did
nothing whatever for the listening.

A folder's menu now offers:

- **Play All Unplayed** -- the newest unplayed episode of *each* show in the
  folder, queued and started. One per show, deliberately: a folder of forty
  shows holds hundreds of unplayed episodes, and a queue of hundreds is not a
  queue, it is something you have to undo.
- **Add All to Queue** -- every unplayed episode, for when you meant it.
- **Move Up** and **Move Down**, which announce the new position ("News, 2 of
  5"). A tree that can only be rearranged by dragging is a tree that cannot be
  rearranged at all with a screen reader.
- **Folder Settings...** -- apply the queue-expiry window, Inbox routing, and
  playback speed to every podcast in the folder at once. Each control starts at
  "change nothing", so nothing is applied by accident, and it says how many
  podcasts it touched.
- **Export This Folder as OPML...** -- hand one folder and its children to
  another machine, or another person, without exporting your whole library.

A folder always means its whole subtree, everywhere: playing "News" plays what
is in "News/Local" too, because that is what somebody looking at the tree
means.

**The Play Queue can be grouped by folder** as well as by podcast (**Group
by**, in the Play Queue). Grouping never changes the play order -- only how it
reads -- and a group header announces itself as one ("News, group, 4
episodes"), so no action can act on a header by accident.

## Moving several podcasts at once

Filing was one show at a time, so tidying forty into six folders was forty
trips through a picker. **Move Several Podcasts to Folder...** lists your
podcasts in a multiple-selection list -- arrows move, Shift and arrow extend,
Ctrl and Space toggles -- with Select All, a running count, and then the same
folder picker once for the lot.

The subscription tree itself is deliberately *not* multi-select. That would
change how every existing selection in it behaves, and multi-select trees are
markedly harder to drive with a screen reader, for a job most people do twice
in the life of a library.

## Smart playlists that can express what you mean

`PlaylistRules` had six filters and ANDed all of them. That is right for
narrowing and useless for the other half of what people want: *anything from
these three shows, or anything I have bookmarked* cannot be said with AND at
all.

Smart playlists now also filter on: **match all or any**, **a library folder**
(subtree aware), **downloaded or not**, **has a note of mine**, **title or show
notes contain**, **where the playhead is** (not started, started, finished --
which is genuinely different from the played mark), and **at most N episodes**,
applied *after* sorting so "the ten newest" is the ten newest.

Beside them is the thing that makes a rule builder usable: **"Matches 23
episodes right now"**, recomputed as you change the rules. Without it, checking
what a filter did meant saving, closing, reopening and reading -- four steps to
answer *did I mean that*.

And because a blank rule builder is where most people stop, **Add Starter
Playlists** creates five worth having: Continue Listening, New This Week, Quick
Listens, Downloaded and Unplayed, Long Reads. They arrive as ordinary editable
playlists rather than built-ins, so renaming, retuning or deleting one works
exactly as it does for a playlist you wrote yourself.

## Chapters for the episodes nobody wrote chapters for

Most podcasts publish no chapter list. A good many of them do something almost
as useful and Cast was throwing it away: they describe their running order in
prose.

> "high school student Tyler Juranek begins a series of short reviews he calls
> Techie Tidbits ... Next, we visit with Gerry Chevalier about the newest
> release of the Victor Reader Stream ... Finally, Matt Roberts brings us part
> one of a demonstration on accessing DVR from Dish Network"

That is a running order: four segments, named, in sequence, **written by a
person**. Cast now takes each described topic and finds where in the episode
its distinctive words actually *arrive*, giving chapters whose titles a human
wrote and whose times were worked out. Measured against hand-built reference
chapter lists, the marks landed within 9 and 15 seconds.

Two details decided the design. The phrases are matched **in order**, because
show notes are written in the order the programme runs, so it is a
sequence-alignment problem rather than a series of independent guesses. And a
topic anchors where it **starts**, not where it is densest -- a
thirty-five-minute interview mentions its guest most often in the middle, and
matching on density put one episode's main segment at 30:00 when it began at
1:09.

**Thorough no longer offers to listen for pauses.** Measured against those same
reference lists, the pause scan scored 0.06 where cutting the episode into
equal slices with no knowledge of it at all scored 0.15. An answer worse than
dividing by *n* is not an answer, and offering it by default spent tens of
seconds making the list worse. Thorough fetches a transcript and works the
sections out of the words; if there is no transcript it says so. Deep still
offers the pause scan, because somebody who chose Deep has said they would
rather have a weak answer than none, and a recording off the radio still uses
it, because for a recording there is nothing else.

**Deep can now transcribe an episode on your own machine**, which it has always
advertised and never actually done. The engine ships in the box -- 40 MB,
CPU-only -- so chapters work the first time you ask, with no download and no
network. It was chosen over models thirty-five times its size on measurement:
it scored *better* (0.372 against 0.316) and ran 4.7 times faster, and the
reason is not transcription quality at all. Its cues break at natural pauses,
so its edges are already plausible section starts.

And **every chapters setting now has a control**. All six were live and all six
were invisible, which is worse than absent: a listener whose chapters were slow,
missing, or being worked out when they did not want them to be had no way to
find the switch that said so. There is now a **Chapters** group in Podcast
Settings, led by the one question most people will ever want to answer -- how
hard should I look? -- with the consequence of that choice spelled out beneath
it in a sentence.

## The columns are yours now

This one is a speech setting wearing a display setting's clothes. An episode
list is read out one column at a time, so the columns *are* the sentence you
hear on every row -- and that sentence had been chosen once, in code, for
everybody. If you work through one show at a time you never needed its name; if
you queue by length you wanted the duration first, not third.

**Subscriptions > Choose Columns...** (Ctrl+Alt+Shift+C) hands it over, for the
episode list, for Downloads, and for Add Podcast's results. There are two lists
in the window -- what is shown, in the order it is read, and what is hidden --
with Move Up and Move Down between them. Not checkboxes: a checkbox in a list is
a state your screen reader has to be asked for, while a position is a place you
land on, and moving something says where it is now.

Hiding a column takes it *out* of the row rather than to the end of it, because
a screen reader reads every column it is given and "last" is still read. It
keeps its place while hidden, so bringing it back later does not send it to the
end of a row you already arranged. Underneath, one line reads out exactly what a
row will say, so you can hear the effect of a change before pressing OK.

Each list offers more than it shows. The episode list can add **Podcast** --
worth having in the Inbox or a playlist where the rows come from several shows,
and pure noise in a list of one show, which is why it is off to begin with --
**Time Left** on an episode you have started, and **Downloaded**. Add Podcast can
add the **Feed Address**, which is what tells two shows with the same name apart.
One column in each list cannot be hidden -- the episode's title, the podcast's
name -- and asking to says so, and why.

Change it while the Manager is open and the list rearranges under you there and
then. Quill Radio gets the same window on its own lists, from the same code:
Quick Actions, listening statistics and folder actions all had to be carried
across from one app to the other after being built twice, and this one was
shared on the first day.

## Smaller things that were missing

- **How long your listening history is kept** is now yours to choose: don't
  keep one, 30 days, 90 days (the default, and what was hardcoded), a year, or
  forever. "Don't keep one" stops the writing rather than deleting afterwards,
  which is what somebody choosing it asked for.
- **Downloads can wait for a connection you are not paying for.** Cast has
  mentioned metered connections in its own source comments for two releases and
  never checked. It checks now, and holds only *automatic* downloads -- one you
  pressed Download for always happens. An unknown connection counts as
  unmetered, because refusing to download on a guess is worse than downloading.
- **Audio Output Device...** is in the Episode menu. Cast plays through
  Windows' default device and cannot switch devices itself, so rather than
  offering a picker that would do nothing, it says so in one sentence and
  offers to open Windows' own per-app sound settings, where the choice sticks.
- **Listening streaks and a Year in Review.** Streaks are **off by default**: a
  streak is a nudge, and a nudge nobody asked for is pressure. Year in Review is
  a few sentences you can read, copy or save -- not a dashboard, because a
  table read aloud is a list of numbers with their meanings three columns away.
  Anything the log cannot support is omitted rather than printed as a confident
  zero.
- **What Quill Radio was asked to do now happens.** From Radio's browse tree
  you could play a subscribed show's episode and nothing else. **Play Next in
  QUILL Cast**, **Add to QUILL Cast Queue** and **Send to the QUILL Cast
  Inbox** are on those rows now, and Cast carries them out at its next launch.

---

## For anybody keeping score on the format

`listening-places/1` is deliberately not a QUILL thing. It is documented,
versioned, and small enough to implement in an afternoon; the identity scheme
is the only part that is hard to change once data exists in the wild, which is
why it is the part the specification is most careful about. If you write a
podcast app and want your users' places to travel to and from QUILL Cast, the
whole of what you need is in `docs/engineering/listening-places-spec.md` and
the fixtures beside it.
