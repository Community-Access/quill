# Quill Radio 3.1 Release Notes

**In development.** This is the note set for the release after 3.0.0, written
as the work lands rather than assembled at the end. Everything below is in the
app today; nothing here is a plan.

For the release before this one, see `release-notes-3.0.md` and its companion
`release-notes-3.0-in-depth.md` -- the latter is what **Help > Release Notes:
The Long Version (Ctrl+Shift+F1)** opens.

---

## The short version

Quill Radio now teaches itself. **Help > Tutorials... (Ctrl+Alt+F1)** opens 36
guided tutorials -- 251 steps, six tracks, about three and a half hours of
material if you worked through every one -- covering every feature the app has,
in the order somebody would actually learn it.

They are not a second copy of the user guide. A tutorial here can **run a step
for you**, and it can **notice when you have done one yourself** and move on
without being asked. That second thing is the part worth reading about.

---

## Part One: What it is like to use

### You open it from wherever you are stuck

The Tutorials window opens on a contents tree: six tracks, each holding its
lessons, each row saying how many steps it has, roughly how long it takes, and
whether you have finished it. A filter box sits above it. Type a word and the
list narrows -- every word you type has to appear somewhere in a tutorial, so
`record tuesday` finds the scheduling lesson without your knowing which field
holds which word.

And type **`here`** and the list narrows to the tutorials about *the window you
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

### Follow me is the part that is new

Tick **Follow me** (it is on to begin with) and the lesson watches the app while
you work. Once a second it asks a question the step declared -- *is something
playing? did your favorites grow? is Browse Stations open?* -- and when the
answer changes it says what it noticed and reads you the next step:

> Done: something is playing now.
>
> Play your first station -- step 6 of 8: Set the volume without leaving the tree...

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
- **It is a courtesy, not a gate.** Nothing is graded, nothing is blocked, there
  is no score and no streak, and every step still has **Next**. A check that
  never comes true costs you one keypress.

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
app to be scored.

### Reading, rather than doing

**Read it all** shows a whole tutorial as one page of text, for when you would
rather read than be walked. And **The whole book as a document** opens all 36
tutorials as one page in your browser, for reading straight through or printing
-- generated from the same lessons the window teaches from, so the two cannot
disagree. (The document states the keys Quill Radio ships with. Only the window
can know the ones you rebound.)

---

## Part Two: What is in the 36

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

---

## Part Three: The reasoning

### Why not just more user guide

The guide is excellent at answering "what does this do". It is bad -- every
guide is -- at answering "what do I do now", because a document cannot see what
you have already done. The whole difference between the two is that a tutorial
knows *where you are in it* and the app can be asked *what just happened*.

### Why a step names a command

Three things fall out of that one decision, and all three were the point:

1. The lesson shows the key you actually have.
2. The lesson can run the step (**Try it**), because a command is a thing that
   can be run.
3. A build check can prove every command a lesson names exists. A tutorial that
   tells somebody to press a key for a command nobody registered is worse than
   no tutorial at all, and that is now impossible to ship.

### Why the watcher watches state

Because "did you do it" and "did you press the key I was thinking of" are
different questions, and only the first one is any of the app's business. Four
routes reach most verbs in Quill Radio. A tutorial that only noticed one of
them would quietly be teaching a preference.

### What it does not do

- **No telemetry.** Your progress is a small file on your own computer, and
  nothing about it goes anywhere.
- **No grading.** No score, no percentage, no streak, no badge.
- **No interruption.** Follow me never takes the keyboard and never moves your
  focus. It speaks, and speaking is all it does.
- **No announcement of what the screen reader already says.** Opening a lesson
  says nothing at all -- focus lands in the step field and your reader reads it.
  Moving *between* steps does announce, because there the text changes under a
  focus that did not move, or under somebody standing in another window doing
  the step.

### One key moved

**Product Requirements... moved from Ctrl+Alt+F1 to Alt+Shift+F1.** The F1
family -- F1 for the control you are on, Ctrl+F1 for the guide, Shift+F1 and
Ctrl+Shift+F1 for the release notes and their companion, Alt+F1 for About -- is
ordered by how often somebody reaches for a door. A new listener reaches for a
tutorial far more often than anybody reaches for the product requirements, so
the tutorials take the shorter chord and the PRD moves out one notch. (The
obvious next chord along, Ctrl+Alt+Shift+F1, was not available: it belongs to a
QuillVille app launcher.)

If you had the old key in your fingers, that is the one thing in this release
that will surprise you.

### What it cost the app

Nothing at runtime. The lessons are ordinary Python data compiled into the app,
the watcher is one timer that reads a handful of values while a lesson is open,
and the whole feature is inert when the window is shut.

---

## For anybody maintaining this

- The lessons live in `quill/core/radio/tutorials/`, one module per half-track,
  wx-free and strict-typed. `validate()` is called by the build.
- `standalone/radio/docs/tutorials.md` is **generated** from those lessons
  (`python -m quill.tools.build_tutorials_reference --write`) and drift fails
  the build (**GATE-TUTDOC**, in the platform scorecard). Do not hand-edit it.
- A step's `check` is answered by `quill/ui/radio/tutorial_checks.py`. Adding a
  new check means adding it there; the content test refuses a check nothing can
  answer, and refuses a `window:` check for anything that is not a real peer
  window.
- Progress is `radio_tutorials.json` in your data folder, classified `cache` in
  the persistence audit: losing it costs a bookmark in a lesson and nothing
  else.

---

## Still to come in 3.1

- A screen-reader pass over the Tutorials window itself -- particularly whether
  the spoken step is the right length, and whether Follow me's "Done: ..." lands
  as help rather than as chatter.
- The same treatment for QUILL Cast, whose lessons would share this machinery
  unchanged.
