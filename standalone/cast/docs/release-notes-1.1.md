# QUILL Cast 1.1 -- Release Notes

QUILL Cast 1.0 was a good podcast library. 1.1 is a podcast *app*.

The difference is one idea, and everything here follows from it: until now QUILL Cast only ever did what you asked, the moment you asked it. It knew how to throw episodes away and nothing about how to fetch them. It held whatever you queued forever. It never mentioned how much disk it was using, or how much of your life you had spent listening. This release closes that gap -- carefully, because an app that starts doing things on its own has to say what it did, and has to be wrong in ways you can undo.

---

## Your episodes are ready before you are

**Automatically download** is the headline, and it is embarrassingly overdue. Podcast Settings now lets you keep the newest 1, 3, 5, 10, or every episode of a show on disk without asking, and any podcast can set its own number from **Settings for This Podcast...**. New episodes arrive downloaded, on subscribe and on every refresh.

Two more switches sit beside it. Anything you add to the **Play Queue** downloads too -- on by default, because an episode you queued is an episode you meant to play. Anything routed to the **Inbox** does not -- off by default, because the Inbox is where episodes wait to be sorted, not a promise to listen to them.

For the two or three shows you never skip, **Auto-Queue New Episodes** goes further: new episodes land straight in the Play Queue, skipping the Inbox entirely. And **Announce New Episodes**, per show, says their titles out loud and in braille when the background check finds them, with a tray notification to match. Both are per podcast, and both are off until you ask -- being told about every feed is being told about nothing.

## Your library, from either app

Quill Radio learned to speak this library's language, and the library got
more honest in return:

- **Folders travel.** Folders you make here are folders in Radio's
  Subscriptions branch, with the same unheard counts on them -- one shared
  implementation, so the two apps can never disagree about what a folder's
  number means. Radio can also make, rename, and delete folders and file
  shows into them; everything lands back in this one library.
- **OPML lands anywhere.** Importing an OPML file in Radio (right-click its
  Podcasts branch) uses the same import engine as Cast's -- folders in the
  file become real folders, duplicates are counted rather than doubled --
  and the result is simply here the next time Cast opens.
- **Unheard counts stop depending on which app refreshed.** Browsing a
  subscribed show's episodes in Radio now syncs them into the library, so
  a show followed there shows its "(N unheard)" badge in both apps without
  Cast having refreshed it first.
- **Mark All as Played knows when it is done.** The Episode-menu and
  manager-menu items now dim when the show has nothing unheard, instead of
  offering to do nothing -- and Radio carries the same verb, on the show's
  own row, over the same shared state.
- **Your position, your speed, and your credentials follow the show.** An
  episode part-heard here resumes at the same spot when played from
  Radio's Subscriptions (and the furthest point wins in both directions);
  a show's saved playback speed applies there too; and a private feed's
  credentials now travel with it, so the feed lists its episodes in both
  apps. Episodes with Podcasting 2.0 chapters get chapter navigation on
  Radio's player as well.

## Your queue looks after itself

A queued episode you never got to is worse than clutter. The queue decides what plays next, so a stale item does not merely sit there taking up space -- it takes a turn.

So any podcast can now set **Expire from the queue**: one day, two, three, a week, a fortnight, a month. Or never, which is the default and stays the default. Daily news show? Two days. Weekly long-form interview? Two weeks. There is deliberately **no global setting**, because the right number differs completely per show and a single "expire everything after N days" is a number nobody actually wants.

Expiring is not deleting. An expired episode moves to **Recently Expired**, a new pinned view in the Podcast Manager beside New Episodes and the Inbox, where it waits seven days. **Restore** puts it back at the end of the queue with a fresh clock; **Restore All** takes the lot. It keeps its downloaded file, its saved position, and its place in its show's episode list the whole time. Only the seven-day sweep removes a downloaded copy, and only for something you chose not to bring back.

Everything it does, it says. A queue that quietly got shorter is exactly the kind of change QUILL Cast does not make in silence.

**On upgrading:** a queue saved before this release has no timestamps to measure against. QUILL Cast reads an unstamped episode as "added just now" rather than "added long ago", so the first launch after updating cannot empty your queue. That was the one genuinely dangerous thing in this release, and it is handled.

## How much have you listened to?

**Listening Statistics**, on the Episode menu, finally answers that. Time listened this week, this month, this year, or all time. How much extra content faster playback bought you -- which is arithmetic, not a guess: ten minutes at 1.5x is exactly five minutes of content you would not otherwise have got through. How many episodes you finished. And a breakdown by podcast, most-listened first.

It is a read-only text field you arrow through line by line and can copy -- the same shape as Player Information, which was already the right answer for a report a screen-reader user needs to review. Not a chart with a text caption bolted underneath.

Durations are read as language. "3 hours, 47 minutes", never `3:47:00`, because a screen reader reads a clock face as a time of day, not a length.

**Export CSV...** saves every session for a spreadsheet. **Clear Statistics...** deletes the log and touches nothing else. Ninety days are kept by default.

**One number is deliberately missing.** Time saved by Smart Speed is not reported, because the silence-trimming path cannot honestly say how much silence it dropped. We could have estimated it from the settings and shown a flattering figure. An invented measurement is worse than an absent one, so the line simply is not there.

## The menus are yours now

**Quick Actions...**, on the Subscriptions menu, gives every content type its own action list, and the order is yours.

Three lists -- episode, podcast, Play Queue -- each reorderable with Move Up, Move Down, and Make Default. Three things follow from the order:

- **The first action is what Enter does.** If you always download before you listen, make Download the default and Enter downloads.
- **The first nine answer to Ctrl+1 through Ctrl+9** in the episode list, so the ones you use constantly need no menu at all.
- **The whole list is the right-click menu order**, so the items you use are the first items, always in the same place, and muscle memory holds.

Nothing changes until you change it. The shipped order puts Play first for an episode and Play Next Episode first for a podcast -- exactly what Enter did before.

## Getting an episode back out

Until now QUILL Cast could copy an episode's link and nothing else. "Share this" has no single desktop gesture, and inventing one would produce a menu item that opens a dialog nobody wants. What a desktop listener actually asks for is a **file** they can put somewhere and an **address** they can paste, so this is three ordinary commands rather than one borrowed metaphor.

**Save Episode Audio As...** is the useful half. Choose where the audio goes and it lands there. It **copies** rather than moves, and that distinction is the whole design: QUILL Cast keeps managing its own downloaded copy, so retention, the storage cap, resume and Remove Downloaded Copy all still work on it, while your saved copy is yours and outside all of it. Moving the managed file would quietly break your place in the episode. An episode you have not downloaded offers to fetch it first and says so, rather than trapping you behind a progress bar of unknown length -- run the command again when it lands. The suggested filename reads "Show - Episode", with anything Windows will not accept replaced rather than stripped (so two episodes whose titles differ only by punctuation do not collapse into one name) and the length bounded, because a Save dialog that opens pre-filled with a name the system rejects is worse than one that opens with a shorter name.

**Copy Podcast Link** sits beside the existing Copy Episode Link. It copies the *feed* address rather than the homepage, because a feed address is the thing another podcast app can actually be given -- which is the point of copying it at all. A local podcast has no feed and says so instead of silently copying nothing.

**Show in File Explorer** opens the folder holding a downloaded episode with the file selected. A streamed episode has no file to show, and says that rather than opening an unrelated folder.

All three are **Quick Actions** entries rather than hard-coded menu items, so they can be reordered, made the Enter default, or reached on Ctrl+1 through Ctrl+9 exactly like everything else on those menus.

## Your place, kept whatever happens

QUILL Cast has always resumed an episode where you stopped. What it did not do
was write that place down unless *you* did something -- pause, stop, change
episode, or quit properly. Every other kind of ending took it with you: a
crash, a power cut, Task Manager, a forced restart, a machine that went to
sleep and did not come back. You would return to your last pause, which after
an hour of uninterrupted listening is an hour ago.

It now saves your position every fifteen seconds while an episode plays, so the
worst any unclean exit can cost is a sentence. It rides a timer that was
already running, so nothing about playback got heavier.

Two smaller things came with it. A position in the first ten seconds is no
longer remembered -- "five seconds in" is the beginning, and being asked
whether to resume there is a question with no useful answer. And your place is
now tied to the **audio itself** rather than to where the file sits, so it
survives moving or renaming a downloaded episode. That last part is
groundwork: recognising the same recording wherever it lives is what will let
your place travel between machines later.

## Your notes, from the player

Episode notes have timestamped the moment and jumped back to it since 1.0. What they lacked was a way in from where you actually make them.

A note is something you write *while listening*, so needing to leave the player, find the episode in the library tree and open its context menu to read your notes back was the wrong shape. **My Notes in This Episode...** now acts on whatever is playing. Selecting a note jumps to it.

**Copy Note** is the other half. Sharing a bookmark means handing somebody something they can act on, and a note's own words pasted alone are a fragment -- there is no way back to the moment they mark. Copy Note puts the episode, the podcast, the timestamp, the note and the audio link together, which pastes into a message as a complete thought. A note whose podcast you have since unsubscribed from still copies; the parts that are gone are simply left out rather than appearing as empty labels.

## Deciding what happens next

**Stop After This Episode** is a one-off: it stops instead of auto-advancing, clears itself when it fires, and never survives a restart. QUILL Cast says "Will stop after this episode" when you turn it on.

Underneath it, two switches in Podcast Settings decide whether anything follows at all: "Play the next episode in the Play Queue" (on -- what QUILL Cast has always done) and "When the queue is empty, keep going with the same podcast" (off, and new). **With both off, playback stops at the end of the episode you started**, which is the entire point of having the pair.

And a real bug, fixed: **finishing an episode from the middle of your queue no longer throws you back to the top.** Play the ninth thing in your queue and the tenth follows, not the first.

**Playback speed is a proper range now** -- 0.5x to 5.0x in tenths, replacing six fixed choices that stopped at 2.0x. **Speed Up** (Ctrl+Shift+Up), **Speed Down** (Ctrl+Shift+Down), and **Reset Speed to Normal** (Ctrl+Shift+0) change it while you listen, and say both the speed and whose it is: the playing podcast's own, or the shared default when nothing is playing.

**Mark All as Played...** clears a show you have given up on, always confirmed by name and count. The episodes stay in your library and downloaded files are untouched; they just leave the Inbox, because the Inbox is unplayed episodes and these are no longer that.

The **sleep timer** gained the two things it was missing. **"End of this episode"** is now a choice, and it tracks the episode rather than a clock -- seek forward and the timer moves with you instead of cutting you off early or leaving you in silence. **Extend 5 Minutes** appears on the timer while it counts down and on the Episode menu, and extending also undoes any fade already in progress, because the point of extending is that you are still listening.

## When a podcast re-publishes an episode

This is small and it is the kind of thing you only notice when it bites.

Publishers re-issue episodes -- a corrected file, a re-cut, one pulled and put
back up. QUILL Cast would refresh the details in place and leave the episode
exactly where it was. If the Inbox had already trimmed it, that meant the
corrected version was sitting in the show's own episode list, where you were
never going to look for it.

It now comes back to the Inbox, and says so in words that do not call it new,
because it is not new: *"Episode 42 was re-published by The Daily, so it is back
in your Inbox."*

What does **not** come back is the interesting part. An episode you have
**played**, one you have **started**, and one you have **queued** all stay where
they are -- as does anything you filed into an Inbox folder yourself. Those are
the same three exemptions the Inbox limits already use, and the reason is the
same: a refresh should not argue with a decision you have already made. Being
finished with something is a decision. So is being halfway through it.

## The Inbox stops growing forever

An Inbox holding every unplayed episode of every routed show, for all time, is not a triage surface. It is a second library.

So any podcast can now cap it: **keep at most N episodes**, and **drop episodes older than** six hours up to two weeks. But the caps only work if they are safe, so:

**Trimming never deletes anything.** A trimmed episode leaves the Inbox and stays unplayed in its show's own list, downloaded file and all.

**Three kinds of episode are never trimmed at all**: anything you have started, anything in your Play Queue, and anything you filed into an Inbox folder by hand. They do not even count toward the cap. That distinction is the whole difference between a helpful limit and losing your place.

## And how much disk is this using?

Until now there was nowhere in QUILL Cast that could answer that. **Downloads...**, on the Downloads menu, now does: total size, a per-podcast breakdown largest first, an Unheard/All filter that says how many rows it hid, and **Remove This Podcast's Downloads...** for one show at a time.

Two automatic rules sit behind it, both off by default: **delete downloads older than N days**, and a **total storage cap** in megabytes. When the cap is exceeded, already-played downloads go oldest first.

**A queued or part-played episode is never removed.** Disk pressure is not a reason to throw away the thing you are halfway through. That rule is why an automatic cap is safe to offer at all, and it means the cap can genuinely be unreachable -- a queue larger than the cap simply stays, and QUILL Cast tells you what it could not free rather than deleting something you were relying on.

**Free Up Space** applies both rules on demand and reports the bytes reclaimed. **Run Housekeeping Now** does the whole pass -- expire, sweep, trim, enforce -- and says everything it did in one sentence. It also runs after every refresh.

## Importing a subscription list that took a decade to build

This one was tested against a real export: 1,307 feeds.

**Nothing blocks the window any more.** Reading, parsing, and adding all happen off the interface thread instead of inside a button handler.

**Duplicates are found properly.** Matching is on a normalized address, so the `http://` and `https://` forms of one feed are correctly recognised as one feed -- old subscription lists are full of both. A file that lists the same show twice imports it once. Two shows that merely share a *title* are both imported and flagged for review, because two different shows genuinely can be called "The Daily".

**QUILL Cast can now tell you which of your feeds are dead.** Tick "Check that each feed is still reachable" and it checks them concurrently once the import is done, with live progress you can hear -- announced every ten per cent -- and a **Stop Checking** button that keeps everything already imported. A feed that asks for a sign-in counts as alive, so your private subscriptions are never reported dead.

**And then you can prune the file.** The import report has **Save Pruned OPML...**, which writes your original file back without the feeds that no longer answer, preserving your folders and everything else in it. Knowing three hundred feeds are dead is only useful if you can act on it.

## Winamp keys -- the same ones as Quill Radio

If you came through Winamp, the classic transport letters now work here: **X** play, **C** pause, **V** stop, **B** next, **Z** previous. Left and Right seek five seconds, Shift+Left and Shift+Right seek thirty. **T** switches between elapsed and remaining. **J** jumps to an episode by name, **Ctrl+J** to a time. **L** opens what is selected.

These are not a second implementation -- they are the same shared key map Quill Radio's recordings player uses. The whole value of muscle memory is that it does not have to be relearned per app.

On by default, with one Preferences checkbox to turn the letters off if you would rather have them for list typeahead.

## Chapters you can skip past

QUILL Cast already found chapters from three different places -- the feed's own chapter document, markers inside the audio file, and timestamps read out of the show notes. What it could not do was *use* them to skip anything.

Now, in the Chapters dialog for the episode you are playing, **Skip This Chapter** marks the ad break, the sponsor read, or the outro you have heard two hundred times. Playback jumps past it and says "Skipping chapter:" and its name. Consecutive marked chapters are stepped over together, and marking everything from here to the end simply finishes the episode normally, so auto-advance and delete-after-play still fire.

Marks last for the listening session only. A chapter you skipped in yesterday's episode says nothing about today's.

## Speed, size, and not falling over

A thousand-show library is not a hypothetical, so:

**A big library no longer stalls the app.** Fully refreshed, a 1,300-show library is around 196,000 episodes -- which takes about seven seconds to write and produces a 164 MB file. That save used to run on every pause, every stop, and every episode change. Above a size threshold, saves and the library-tree rebuild now settle onto a short timer instead of running in the middle of your keystroke. Below it, nothing changes at all and saves stay immediate. Closing the app always writes everything out first.

**Expanding one podcast is no longer the whole library.** A show's episodes are built when you expand that show, not for every show up front -- which on a large library was around 196,000 tree items, rebuilt on every save.

**Long lists say what they are not showing.** A cross-show view like New Episodes fills the newest thousand rows, and the status line tells you how many there are in total and how to narrow it, rather than attempting to list two hundred thousand episodes and hanging.

## Also in this release

- **Settings for This Podcast...** gathers everything that only makes sense one show at a time -- auto-download, auto-queue, announcements, queue expiry, speed, Inbox caps, download age limit. **Follow the Shared Defaults** drops every override at once, and leaving a field on the shared default stores no override at all, so changing the global later still reaches that show.
- **Read the podcast name first**, an accessibility preference for cross-show lists. In two hundred rows from forty shows, whichever name comes first is what you can skim by first letter -- and which that should be depends entirely on how you look for things.
- **Start on this view**: choose whether QUILL Cast opens on New Episodes, Continue Listening, the Inbox, Favorites, Recently Expired, or the top of the tree.
- **Group the Play Queue by podcast**, with move-group-to-top, up, down, and bottom. Forty items from four shows is a list nobody can hold in their head. Four groups is.
- **Export My Data...** writes your subscriptions, folders, queue, playlists, episode notes, listening statistics, and recently-played list to one readable JSON file. OPML covers subscriptions and nothing else.
- **Delete All Podcast Data...** starts you over, confirmed twice, with downloaded files as a separate question -- "start over" and "reclaim the disk" are not the same wish.

- **Every app in the family has its own icon now.** QUILL Cast's was always its own -- a microphone capsule under waves, which is what tells it apart from Quill Radio at a glance -- but three of its siblings were shipping byte-identical copies of Radio's icon and two more had none at all. They now come from one shared design system, so no two Quill apps can wear the same face. Cast's own picture is unchanged; its waves were redrawn a touch heavier to match Radio's exactly, because the two apps are the closest pair in the family.

## What has not changed

QUILL Cast still collects no telemetry of any kind, still shares one library with QUILL and the rest of the family, still works entirely from the keyboard, and still says what it did. Everything in this release that acts on its own -- an expiry, a trim, an eviction, an automatic download -- announces itself, and every one of them can be turned off.

See the User Guide for how each of these works, and `CHANGELOG.md` for the versioned history.
