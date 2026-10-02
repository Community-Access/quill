# QUILL Quality Plan, Progress, and Verification

Consolidated 2026-10-01. This is the single source for the Cast redesign,
family reliability work, completed-change evidence, and manual screen-reader
testing. Consolidation does not mark unfinished code or human acceptance done.
Historical dates, test results, and implementation claims below retain their
original context and must be reverified before changing completion status.

## Progress Dashboard

Updated 2026-10-02: F-01, F-02 and the Activity half of F-10 shipped (one shared result model, Activity window and F9/Shift+F9 in every app; guarded settings and history writers). Previous update 2026-10-01 (second pass). **T-00 and T-01 are done**: the consolidation and the Phase 0/1 working tree were committed as `fef27b3` and pushed to main. **Active: Cast Phase 1, one feature per commit, each pushed to main with the gates green and the Cast user guide, PRD and release notes updated in the same commit.** The Phase 1 section below was re-verified against the source on 2026-10-01; its nine `[x]` rows were committed in `fef27b3`, and the rest are being closed one commit each; the table below is recomputed from the trackers on every commit, never edited by hand. F-05 (asynchronous Lite file opening) stays queued behind the Cast work.

These are grouped tracking rows, not independent bugs. Shared work can satisfy more than one group. Older pending claims are not newly verified by this consolidation.

The following table separates implementation, its delivery gate, and human acceptance.

| Category | Remaining | Status |
|---|---:|---|
| Family reliability findings | 4 | Partially implemented; F-04, F-05, F-06 and F-11 done 2026-10-01; F-01 and F-02 done 2026-10-02 |
| Family product requirements | 6 | Includes Gemini review; transport feedback (X-06) done 2026-10-01 |
| Cast Phase 1 code and tests | 1 | Re-verified 2026-10-01; being closed one commit at a time |
| Cast Phases 2-7 | 6 | Grouped implementation phases |
| Cast follow-on integrations | 3 | Remaining |
| Manual screen-reader scenarios | 73 | Human acceptance pending |
| **Total tracked rows** | **93** | **20 code/delivery groups + 73 manual scenarios** |

Code/delivery subtotal: **20**.

**Next releases** (Jeff, 2026-10-01): Quill Radio **3.1.1** (not yet tagged;
the code already says 3.1.1), QUILL Cast **1.1.0**, QUILL Lite **1.2.0** (the
code still says 1.1.2 and is bumped at release, not before -- the 1.1.1
story is why), Quill Converter **1.0.0** (first release). Release notes
and changelogs label unreleased work with these numbers. Manual scenarios remain in their testing section; they are not duplicated in the bottom code tracker. Maintain this table, bottom checklists, and VS Code todos in the same progress update. Remove completed code rows only after tests and documentation are recorded; never mark human testing passed automatically.

## Contents

- [Progress dashboard](#progress-dashboard)
- [Cast product and UX plan](#cast-product-and-ux-plan)
- [Family reliability review](#family-reliability-review)
- [Screen-reader testing handoff](#screen-reader-testing-handoff)
- [Completed changes and validation](#completed-changes-and-validation)
- [Remaining code work](#remaining-code-work)

Update the bottom code trackers as work is verified. Move finished implementation
and test evidence into Completed Changes and Validation; add its UX testing
script to Screen-Reader Testing Handoff. Trim obsolete pending text without
discarding design requirements or implementation history. Manual listening
stays pending until a human records it as passed.

## Cast Product and UX Plan

Original document title: QUILL Cast: the shape of the app. The status and tree
snapshots in this preserved plan describe their original date, not a new audit.

| | |
|---|---|
| Status | Active. Written 2026-09-30 from a first real session of use; revised the same day, twice, as Jeff asked for the whole UX rethought rather than patched, then for every window and flow to be covered. This is the complete version. Nothing further is built until Jeff has read it. |
| Owner | Jeff Bishop |
| Author | Fable, as senior designer, at Jeff's request. |
| Scope | QUILL Cast only. Where Quill Radio already has the answer, Cast copies it -- by shared module, never by a second implementation. |
| Lives | Here, at the root, gitignored like `ear.md`. It describes work rather than being it. |

### 0. How to read this

Section 1 is what happened. Section 2 is why. Section 3 is the principles, each
with its test. Section 4 is the main window in full, including the Places list
and how a listener makes it their own. Section 5 is Now Playing; 5b is
Notifications; 5c is reading and copying the notes; 5d is watched folders; 5e
is when Cast looks for new episodes. Section 6 is every other
window, every one, with what it becomes; 6b is what a survey of all 43 of them
found, with where each finding is fixed; 7 is the context menus; 8 is the
keyboard. Section 9 is the user
flows, start to finish, as spoken. Sections 10 to 14 are the cross-cutting
systems: speech, visuals, words, settings, help. Section 15 is the phases and
what is already done. Section 17 is the switch for every feature. Section 18 is
what Cast should gain, not only fix. Section 19 is what Radio has that Cast
should. Section 20 is the state of the tree right now. Section 21 is the
technical notes: data model, modules by phase, gates, threading, Windows facts,
performance, and the hazards met today.

A reader with ten minutes should read 2, 4, 15 and 20. An implementer starts
at 21.

### 1. What happened

On 2026-09-30 Jeff used Cast for the first time as a listener rather than as its
author, and reported what he met, in order. Twenty-odd things in about two hours.
Most were not polish. The list is kept because it is the only usability study
this app has ever had, and it was run by exactly the person the app is for.

1. The edit fields in Add Podcast had no accessible name.
2. Preview did nothing. (It had never worked: a wrong function name, failing
   silently into a status label nobody hears.)
3. The Subscribe button did not know you already followed the show.
4. No context menu on the results list.
5. Combo boxes had no accessible names.
6. "The UI is not reacting when buttons are pushed."
7. Backups, OPML, exports: "a bit of a UI mess from a basic user perspective."
8. "I land in the library on Favorites. If I tab I see Play. Play what?"
9. "Left and right say nothing is playing." (Arrows were being eaten in the
   tree. A keyboard listener could not expand a folder.)
10. Remove the Community menu.
11. Alt+S invoked Stop instead of opening the Subscriptions menu.
12. The menu bar should always be visible; there should be a Window menu.
13. Favorites shows a count but cannot be expanded. Nor Inbox. Nor New Episodes.
14. View should sit where View sits.
15. Quillins should not show unless in Advanced mode.
16. Arrow to an episode, press Play: "select a show."
17. Volume and speed are not discoverable. Cast needs a Now Playing window.
18. Add Podcast with no Remove Podcast beside it.
19. "This Open Manager button needs a better name. That is confusing as all get out."
20. The tree should be searchable, like Radio. Search the whole library.
21. "Think creatively if we have to reorganize windows, layout, constructs."
22. Launch place configurable in settings.

### 2. The three things underneath

These are not twenty-two bugs. They are three structural facts, and every item
above is a symptom of one of them.

#### 2.1 Two apps pretending to be one

The main window is a tree and five buttons. The Podcast Manager is a second,
larger window with its own tree, an episode list, a filter row and twenty
buttons. They overlap almost entirely and differ in details nobody can predict.
"Open Manager" is confusing because nobody can say what the main window is *for*
if the Manager exists -- and the honest answer is that the main window is the
part that got built first.

Radio does not have this. Its main window is the app. Earshot does not have
this: it has places, not modes. **Cast will have one window.**

#### 2.2 One tree, five kinds of thing in it

The library tree mixes pinned views, folders, podcasts, episodes, "more" rows
and, when empty, action rows. A listener arrowing down it never knows whether
Right-arrow will open a place, a folder or a show, whether Enter will play or
navigate, or whether a count means episodes or podcasts. That is the deeper
cause of "confusing as all get out": not any one row, but that the rows do not
share a grammar.

Earshot, Outlook and Radio's Browse all answer this the same way. **A flat list of
places on the left. The content of the chosen place on the right.** Two lists,
each of one kind of thing. Screen readers handle list-then-list far better than
one deep mixed tree, and a listener learns the shape in a minute: arrow down the
places, Tab into what is there.

#### 2.3 Silence, and controls that describe nothing

Every "the button did nothing" was a button that did something invisible: a
status label changed (silent to a screen reader), a background task failed
(silent), a mode switched (silent). And the controls that did speak said the
verb without the object -- "Play", "Add to favorites" -- on a window where the
object changes with every arrow key.

**Every action has a spoken outcome, or a spoken reason it had none. Every
control names the thing it will act on.**

### 3. Principles, each with its test

A principle nobody can test is a preference. These have tests, and where the
codebase's idiom allows, gates.

| # | Principle | The test |
|---|---|---|
| P1 | **One primary library window.** Places on the left, content on the right; anything that needs independent persistence or a different reading task is a deliberate peer window in the Window menu. | `manager_dialog.py` does not exist. Every former Manager action is reachable from the main window, and every peer has the shared surface contract. |
| P2 | **Every node opens.** Every row with a count opens to what it counts. | A test walks the model: any row whose label carries `(n)` has children or content. |
| P3 | **Controls name their object, in the text the reader actually reads.** For a button on Windows that is its visible label, never `set_accessible_name`, which wxMSW ignores. No button has a static label while a selection exists. | `transport_intent` tests (done); the button row refreshes its labels on every selection change; a gate that no `set_accessible_name` call targets a `wx.Button` in Cast. |
| P4 | **Nothing is silent.** A status-line change is spoken; a background failure is spoken and lands in Recent Problems. | One helper (`say_status`); a banned-pattern rule on bare `_status.SetLabel` in `quill/ui/podcasts`. |
| P5 | **Mnemonics never collide across the window.** A control and a top-level menu never share an Alt letter. | GATE-15, `quill/tools/check_menubar_mnemonics.py` (done). |
| P6 | **Every list has a keyboard context menu**, and every row's menu has the same shape -- disabled, never absent. | Gate: every `ListCtrl`/`TreeCtrl`/`ListBox` in `quill/ui/podcasts` binds `EVT_CONTEXT_MENU`. |
| P7 | **Words are the listener's.** Follow, unfollow, podcast, episode, unheard. Never subscribe, show, feed, unplayed in user-facing text. | A wordlist test over string literals, with a reviewed allowlist (OPML keeps "subscription list"). |
| P8 | **Simple by default.** A newcomer learns the whole menu bar in one sitting. Advanced is one switch away and hides nothing the palette cannot reach. | `menu_mode` tests (done). |
| P9 | **Radio's answer is Cast's answer** wherever both face the same question: search that flattens, the status bar, the Window menu, peer windows with menu bars, the sleep timer, the transport keys. | Parity by shared module and surface contract, never by a second implementation. |
| P10 | **Search is one box and it finds everything.** Places, podcasts, episodes, notes, transcripts -- one field, results replace the content pane, each row says what it is and where it lives. | One search core, used by the main window and nothing else. |
| P11 | **Every label is created before its control.** On wxMSW that ordering *is* the accessible name. | GATE-CTLLABEL, `quill/tools/check_control_labels.py` (done; 165 found, 146 remain, may only fall). |
| P12 | **A question dialog asks one question and names what is at stake.** Never "are you sure?"; always the title of the thing and what survives. | Wording lives in `core/podcasts/*_words.py` modules, never retyped; a test per question. |

### 4. The main window

```
QUILL Cast                                                    [menu bar, always]
  Podcasts  View  Episode  Downloads  Window  Help                      (Simple)
  Podcasts  View  Episode  Downloads  Quillins  Window  Help          (Advanced)

  Now playing: The Daily -- Thursday's episode          12:04 / 31:50   1.5x
  Find: [                                              ]          (Ctrl+F)

+-- Places -------------+-- Inbox (12) --------------------------------------+
|  Inbox (12)           |  Thursday's episode -- The Daily        31m   New  |
|  New Episodes (31)    |  Episode 412 -- Accidental Tech Podcast 2h   New   |
|  Continue Listening 3 |  ...                                               |
|  Favorites (4)        |                                                    |
|  Personal Audio (2)   |                                                    |
|  Play Queue (4)       |                                                    |
|  Downloads (6)        |                                                    |
|  Podcasts (40)        |                                                    |
+-----------------------+----------------------------------------------------+
| [Play Thursday's episode] [S&top] [Unfollow The Daily] [Add Podcast...]     |
| Play | Mute | Volume 70% | Speed 1.5x | Queue 4 | Inbox 12 | Sleep | 14:02  |
+----------------------------------------------------------------------------+
```

#### 4.1 The Now Playing line

One read-only line at the top, in a larger weight, naming the playing episode
and podcast, the position and duration, and the speed when it is not 1x. Ctrl+T
speaks it (the What's Playing key Radio uses). It is a reviewable field, not a
StaticText, so a screen reader can arrow through the exact spelling of a title.
It is never announced on its own: playback announces the title when it starts,
and this line is where somebody goes to hear it again.

Visually it is the one thing a sighted listener sees first, which is why it is
first and why it is larger.

#### 4.2 Find

One box, Ctrl+F from anywhere in the window. Typing flattens the content pane
into matches across the whole library -- podcasts, episodes, show notes, your
notes, downloaded transcripts -- each row saying what it is and where it lives:

    Thursday's episode -- an episode of The Daily, in News
    The Daily -- a podcast, in News (3 unheard)
    "...mentioned the Bristol bus boycott..." -- in the transcript of Episode 412

Matches are ranked: places first, then podcast titles, then episode titles, then
notes, then transcript text; within a rank, newest first. The status line under
the box says "14 matches for bristol" and is spoken once the typing pauses, not
on every keystroke. Enter on a match goes to it (a podcast opens in Podcasts; an
episode selects itself in its place; a transcript hit opens the transcript at the
line). Escape, or emptying the box, restores the place that was showing and puts
the cursor back where it was.

This one box replaces Search Everywhere, the Manager's Find-in-this-podcast, and
the per-list filter rows, which were four searches with four answers. The
Manager's episode-state filter (unplayed, downloaded...) becomes a View-menu
choice that applies to every episode list, so it is one setting, not one per
window.

Radio's principle exactly: a filter flattens the view so results are one
arrow-key apart.

#### 4.3 The Places list

Flat, and it never changes shape. Eight rows, each with its live count:

| Place | Counts | Opens to |
|---|---|---|
| Inbox | unheard episodes routed here, after caps and filters | an episode list |
| New Episodes | unheard episodes, everywhere | an episode list |
| Continue Listening | episodes with a saved place | an episode list, most recent first |
| Favorites | favourited podcasts | a podcast list |
| Personal Audio | your own files | an episode list (they are one podcast) |
| Play Queue | queued episodes | an episode list, in queue order |
| Downloads | episodes on this computer | an episode list |
| Podcasts | podcasts you follow | the folder tree |

The order above is the default. **The list is fully the listener's** (Jeff,
2026-09-30: "fully configurable, including the order"):

- **Reorder in place**: Alt+Shift+Up and Alt+Shift+Down on a place move it --
  Radio's chord exactly (Jeff: "handle up and down like we did in radio"),
  caught in the frame's char hook as Radio does because Windows routes
  Alt+arrow to the menu system before a tree or list ever sees it. The same
  chord reorders a podcast or folder in Custom Order, so one gesture means
  "move this" everywhere in the app. The move is spoken: "Continue Listening
  moved to first."
- **Hide and show**: Delete on a place hides it (spoken, undoable); View >
  Places... opens the chooser -- a reorderable list with Up, Down, Show and
  Hide buttons, the house pattern for a wx list (no checkboxes in a list
  control). A hidden place is still reachable by its key and by Go To, so
  hiding is a shorter list and never a lost feature.
- **Rename**: F2 on a place, as today's view rename; the shipped name is one
  key away in the chooser.
- **Reset to the default order** in the chooser.

The order and the hidden set are one setting, `places_layout`, stored with the
library so it travels with a synced data folder. A row with nothing in it stays
in the list and says so on arrival: "Play Queue, empty -- Add to Queue on any
episode puts it here." A place whose *feature* is switched off in Customize
Features (section 17) is not in the list at all, which is the difference
between hiding a place and not having one.

The same applies to the folder tree under Podcasts: Custom Order already exists
for podcasts within a folder and folders within a folder; Alt+Up/Down works
there today. Playlists, when any exist, appear as a place between Favorites and
Personal Audio and obey the same rules.

Arrow keys move between places. Enter or Right-arrow moves into the content
pane. The Applications key on a place offers what the place can do as a whole:
Mark All as Played, Clear the Queue, Refresh All, Choose Columns.

#### 4.4 The content pane

One control whose *kind* depends on the place; the heading above it names the
place and its count, so a listener arriving by Tab hears where they are.

**The episode list** (Inbox, New Episodes, Continue Listening, Personal Audio,
Play Queue, Downloads) is a report list with columns. Default columns: Title,
Podcast, Duration, Status (Jeff, 2026-09-30); the rest -- Published, Description,
Chapters, Notes -- through Choose Columns. Each row is read column by column, so
Title leads and Status ("New", "12 min in", "Downloaded", "Played") closes.
Enter plays. Space adds to the queue (the same key Radio's Browse uses to
favourite). Delete removes from *this place* -- from the queue, from the Inbox,
from Downloads -- and says what it did and what survived; it never deletes an
episode. Multiple selection works everywhere and every action says its count.

**The podcast list** (Favorites) is the same report list with podcast columns:
Title, Unheard, Last new episode, Folder. Enter opens that podcast's episodes in
place (the heading becomes "The Daily (3 unheard)", Backspace returns).

**The folder tree** (Podcasts) is the one tree in the app, and the only place
nesting genuinely helps: folders, podcasts under folders, episodes under
podcasts, each level expanding on demand as it does today. A folder row counts
its podcasts; a podcast row counts its unheard. Left-arrow at a top-level row
returns to the Places list.

Left-arrow at the top of any content pane returns to Places. The two panes share
one selection; the button row, the Episode menu and the status bar act on it.

#### 4.5 The button row

Four buttons, and each names its object **in its visible label** -- not in its
accessible name. The survey (6b) caught what Phase 1 got wrong: on wxMSW a
button is self-labelled and `set_accessible_name` is inert (`accessible_names.py`
says so; MSAA and UIA never read it), so a button whose *name* says "Play
Thursday's episode" and whose *label* says "Play" is heard as "Play". The
object has to be in the label. The row is a fixed-width sizer with each button
given its share, and the label is elided at forty characters, so nothing
reflows as the selection changes. Refreshed on every selection change:

- **Play / Pause / Resume** -- "Play Thursday's episode", "Resume The Daily,
  Episode 4", or, stopped with nothing playable under the cursor, "Play. Nothing
  is selected that can be played -- choose a podcast or an episode first, or use
  Continue Listening."
- **Stop** -- enabled only while something is playing.
- **Unfollow <podcast>** -- enabled with a podcast selected, or with an episode
  selected (its podcast); through the shared undoable prompt.
- **Add Podcast...**

Mnemonics are chosen against the menu bar's letters (GATE-15): Pla&y, Pau&se,
Re&sume, S&top, &Unfollow, &Add. The three transport labels matter separately
-- the survey (6b) found that the moment anything plays, "&Pause" reclaimed
Alt+P from the Podcasts menu, and GATE-15 could not see it because it read only
the static "Pla&y" literal. So the three labels live in
`transport_intent.button_label`, the gate reads that function's outputs as
well as the panel's literals, and no state of this row ever shares Alt+letter
with a menu.

#### 4.6 The status bar

Nine cells, F6 in and out, arrows between, Enter activates, Applications key for
each cell's own menu (done, Phase 1, modelled on Radio's): Play/Pause · Mute ·
Volume · Speed · Queue · Inbox · Downloads · Sleep timer · Time. Action cells'
labels *are* their actions and flip with state; readout cells answer Enter with
something useful. Hidden by View > Show Status Bar; it refuses Tab focus so it
costs nothing until F6.

#### 4.7 The menu bar, row by row

Every row shows its key. Advanced-only rows are marked (A) and are omitted in
Simple mode, never greyed; every one of them stays reachable by name in the
Command Palette. Order follows Microsoft's: the app's own menu, then View.

**Podcasts** (Alt+P)
- Add Podcast... Ctrl+N
- Unfollow <selected>... Delete
- Refresh All Now F5
- Feed Check... Ctrl+Shift+C
- New Folder... Ctrl+Shift+F
- Sort Podcasts > A to Z / Z to A / Custom Order
- Add Personal Audio... Ctrl+Alt+L
- Scan Watched Folders Ctrl+Alt+W
- Follow ACB Media Podcasts Ctrl+Alt+B
- (separator)
- Settings for This Podcast... Ctrl+Alt+,
- Preferences... Ctrl+,
- (separator, A)
- Import OPML... (A) · Export OPML... (A)
- Back Up My Podcasts... (A) · Restore from a Backup... (A)
- Export My Data... (A) · Delete All Podcast Data... (A)
- Podcast Index Credentials... (A)
- (separator)
- Send to Tray Ctrl+W · Exit Ctrl+Q

**View** (Alt+V)
- Inbox Ctrl+Shift+I · New Episodes · Continue Listening · Favorites ·
  Personal Audio Ctrl+Shift+U · Play Queue Ctrl+Shift+Q · Downloads Ctrl+D ·
  Podcasts Ctrl+Shift+P
- (separator)
- Find Ctrl+F
- Show > All episodes / Unheard only / Downloaded only / Started only (the one
  episode filter, applied to every list)
- Sort Episodes > Newest first / Oldest first / By podcast / By duration
- Hide Caught-Up Podcasts Ctrl+Shift+H
- Inbox Folder... Ctrl+Shift+O
- Choose Columns... (A) · Quick Actions... (A)
- (separator)
- Show Status Bar Ctrl+Shift+B
- Advanced Features Ctrl+Alt+Shift+G
- Customize Features...

**Episode** (Alt+E) -- acts on the selection, or on what is playing
- Play/Pause Ctrl+P · Stop Ctrl+. · Mute Ctrl+Alt+M
- Volume Up/Down Ctrl+Up/Down · Speed Up/Down Ctrl+Shift+Up/Down · Reset Speed
- Skip Forward/Back Ctrl+Right/Left · Next/Previous Chapter Ctrl+Alt+Right/Left
- Go to Position... Ctrl+Alt+J
- (separator)
- Add to Queue Space · Play Queue Run > Next / Previous / Mark Played and Next
- Play an Unheard Episode · Play Queue Shuffled · Clear Entire Queue...
- (separator)
- Mark as Played · Mark All as Played... Ctrl+Shift+E · Keep This Episode
- Download / Remove Download · Refresh Episode Audio...
- Remove from Inbox · File to Inbox Folder...
- (separator)
- About This Episode... Ctrl+Shift+A · Show Notes... · Transcript... ·
  Chapters... · Add Note... Ctrl+Alt+N · Share...
- (separator)
- Sleep Timer... Ctrl+Alt+T · Sleep at End of This Episode · Extend 5 Minutes
- Stop After This Episode
- Sound Enhancements... Ctrl+E · Audio Output Mode · Audio Output Device...
- Skip Settings... (A) · Listening Statistics... (A) · Recently Played >

**Downloads** (Alt+D)
- Downloads... · Pause All · Resume All
- Free Up Space (A) · Run Housekeeping Now (A)

**Quillins** (A) -- as today.

**Window** (Alt+W) -- the shared menu: every open window numbered, Ctrl+1..9,
Ctrl+Tab / Ctrl+Shift+Tab. Now Playing is always row 2, whether or not it is
open, so Ctrl+2 always reaches it.

**Help** (Alt+H)
- Command Palette... · Go To... · Tutorials... Ctrl+Alt+F1 · User Guide ·
  Release Notes · Keyboard Shortcuts Sheet...
- Get Help from Support... · Recent Problems... · Quiet Hours... ·
  Export/Import My Setup...
- Keyboard Shortcuts... (A) · Global Hotkeys... (A) · Media Tools (A) ·
  Get FFmpeg... (A) · Product Requirements (A) · Redeem Unlock Code... (A)
- Check for Updates... · About QUILL Cast

#### 4.8 Launch

The window opens on the place chosen in Preferences (done, Phase 1). The default
is the automatic rule: the Inbox if anything is waiting, else Continue Listening
if anything is half-heard, else Podcasts. Focus is on that place's content pane,
on its first row. If Resume Last Episode on Launch is on, playback starts and the
Now Playing line fills; focus does not move.

#### 4.9 Empty states

An empty pane says what fills it, on arrival, once:

- Podcasts, empty: three rows that act on Enter -- Add a Podcast by Name, Add a
  Podcast by Address, Import from OPML -- as today.
- Inbox, empty: "The Inbox is empty. Episodes arrive here from podcasts set to
  send new episodes to the Inbox, in Settings for This Podcast." If a folder
  scope is in force: "Nothing in the Inbox for News. The rest of the Inbox is
  still there -- choose All podcasts in View > Inbox Folder."
- Continue Listening, empty: "Nothing half-heard. Start any episode and stop
  part way, and it will be here."
- Play Queue, empty: "The queue is empty. Space on any episode adds it."
- Downloads, empty: "Nothing downloaded. Download on any episode keeps it here."
- Personal Audio, empty: "Add Personal Audio, in the Podcasts menu, imports your
  own recordings and audiobooks. The original file stays where it is."
- Favorites, empty: "No favourites yet. Add to Favorites on any podcast."

### 5. Now Playing

Window 2. A console a listener can live in for an evening without touching the
library. Opened from Window > Now Playing, Ctrl+2, or the status bar's Play cell
menu. With the Preferences checkbox on (off by default, Jeff, 2026-09-30), it
comes to the front when playback starts.

```
Now Playing                                                    [menu bar]
  The Daily
  Thursday's episode
  Playing from: the Inbox

  Position  [========|------------------------]  12:04 of 31:50
  [Play/Pause] [Stop] [Back 30s] [Forward 30s] [Previous Ch] [Next Ch]

  Speed    [1.5x  v]     Volume [======|---] 70%    [Mute]
  Sleep timer: off  [Set...]  [End of episode]  [Extend 5 min]

  Chapters (4)
    1. Introduction                0:00
    2. The main story              2:14  <- playing
    3. Listener questions         19:40
    4. Credits                    30:02

  Show notes  [reviewable text ......................................]
  Your note   [editable ...........................................]

  [Add to Favorites] [Mark as Played] [Share...] [About This Episode...]
```

- The position slider speaks minutes and seconds as it moves; Left/Right nudge
  five seconds, Page keys thirty, Home/End to the ends. It is a real slider, so a
  screen reader reads it as one.
- Speed is a choice of the nine speeds plus Custom (the Manager's chooser,
  kept). Volume is a slider. Both are the only *controls* for these anywhere;
  everywhere else they are keys and status-bar cells.
- The chapters list is a report list; Enter jumps; the playing chapter carries
  "playing" in its Status column and the list follows playback without moving
  the cursor.
- Show notes are the reviewable text field from today's Show Notes window, with
  its links list one key away (the "Links in These Show Notes" window survives
  as that key).
- Your note is the Episode Notes field, editable in place, saved on blur.
- The bottom row acts on the playing episode.
- The menu bar is the main window's, installed on this frame (Radio's `_show`),
  so nothing is lost by being here. Ctrl+1 returns to the library.
- Announcements: the window announces nothing on open beyond its title (the
  reader does that); chapter changes announce the chapter title, as they do
  today; the sleep timer announces its last minute.

This window absorbs: Player Information (its lines become the Playing-from line
and the About window), Go to Position (the slider), the Speed chooser, Volume,
the Sleep Timer dialog's readout (the Set... button keeps the dialog for typing a
number).

### 5b. Notifications

Jeff: "don't forget about notifications like Quill Radio has. That has to be
integrated somehow, with a notification window."

**What exists.** The record is shared: `quill/core/notifications.py` is one
bounded store both apps write to, and `quill/ui/notification_center.py` is one
window both apps open -- newest first, one line per notice, the word "New" as
the unread marker so it survives being read aloud. Cast already mixes it in
through `ListeningAppSupportMixin` and already has the door back
(`open_notification_target`: Enter on a notice selects the podcast it was
about). The support menu already puts "Notifications..." in Help. A toast is
the optional louder half on top, and the quiet alert mode makes the window the
whole of it.

**What is missing in Cast**, and what Phase 2 adds:

- **An unread count where a listener meets it.** A status-bar cell,
  "Notifications 3", between Downloads and Sleep timer; Enter opens the window;
  its menu offers Mark All as Read and Clear. Empty when nothing is unread, so
  it costs nothing when there is nothing.
- **A row in the View menu** (Ctrl+Shift+N) beside the places, not only in Help
  -- notifications are a place you go, and Help is where nobody looks for what
  just happened. The Help row stays for the shared shape.
- **In the Window menu**, as a peer window with the menu bar, so Ctrl+number
  reaches it and Escape returns to where you were.
- **Actions on a new-episode notice** (ear.md R9): the row's context menu and
  its Enter offer Play Now, Add to Queue, Go to the Podcast, Mark Read. Enter
  keeps meaning "go to it"; the other three are one key deeper. A toast for a
  new episode carries the same Play Now and Add to Queue buttons, which the
  shared `toast.show_toast` already supports through `_add_action`.
- **A digest on launch**, one sentence, when anything arrived while Cast was
  closed: "Since yesterday: 4 new episodes from 3 podcasts. They are in the
  Inbox." Off in Quiet Hours; off by a Preferences checkbox; never more than
  one sentence.
- **What Cast notifies about**, each with its own switch in Settings for This
  Podcast (per podcast) and Preferences (the defaults): a new episode; a feed
  that has failed N times (already latched); a podcast gone quiet (already
  latched); a download finished when it was started by hand; the sleep timer's
  last minute; a Personal Audio import finished. Nothing else. Every one is a
  record first and a sound second.
- **The alert mode** -- alert, quiet, silent -- is Radio's setting with Radio's
  wording, shared, in Preferences.

### 5c. Reading the notes

Jeff: "we need a rich way to read episode and show notes, or to view in
browser. A show links button should also be visible so that you can get a list
of links to arrow through with titles and you can copy to the clipboard, view
in browser or close."

Show notes are where a podcast tells you what an episode is; today Cast shows
them as one plain-text block with the HTML stripped, and the links list is a
separate dialog few people find. The notes deserve to be **read**, not
extracted.

**The Notes reader** is one surface used in three places: the show-notes pane
in Now Playing, the Show Notes peer window for any other episode, and the
podcast's own description in About This Podcast. It is a read-only rich text
control, not a plain one, and it keeps the notes' structure:

- **Headings, paragraphs, lists** survive from the HTML, so a screen reader's
  heading navigation works inside the notes (H, Shift+H) exactly as it does on
  a web page. A five-hundred-word episode description with three sections is
  three headings away, not a wall.
- **Links are links.** Tab moves between them; Enter opens one in the browser
  after saying its title; the link text is spoken as the link, never the raw
  address.
- **Timestamps are links to the episode.** "12:34" in the notes seeks the
  playing episode there on Enter (section 18, item 2). If the episode is not
  playing, Enter offers to play it from that point.
- **Find inside the notes** (Ctrl+F while in the reader) with the count
  spoken; F3 for next.
- **Copy**, properly (Jeff: "copy show notes to the clipboard in full form
  either as plain text without links or fully formatted, configurable").
  Ctrl+C copies the selection as text, as any field does. **Copy Notes**
  (Alt+C, a visible button beside Links) copies the *whole* notes in the
  format chosen in Preferences, and its menu -- the Applications key on the
  button, or its dropdown -- offers every format so the choice is one key
  away without a trip to Preferences:
  - **Plain text** -- paragraphs and lists kept as lines, headings as lines,
    links reduced to their text, timestamps kept. The shipped default; what
    pastes cleanly into an email or a chat.
  - **Plain text with links** -- the same, with each link's address in
    brackets after its text, so nothing is lost and nothing is hidden.
  - **Markdown** -- headings, lists, links and emphasis as Markdown. QUILL is
    a writing app; this is the format a QUILL document wants, and the one a
    listener keeping notes in a text file wants.
  - **Formatted** -- HTML on the clipboard as `CF_HTML` with an RTF copy
    beside it, so Word, Outlook and QUILL's rich editor paste the formatting
    and Notepad pastes text. Images referenced by address, never embedded.
  Every copy is spoken: "Copied the show notes as plain text, 412 words."
  The same four formats apply to a podcast's description and to a
  transcript, from the same button, so there is one Copy vocabulary. The
  conversion lives in one wx-free module (`core/podcasts/notes_export.py`)
  with a test per format, because "copy as Markdown" that drops a heading is
  worse than no Markdown at all.

**The Links button** (Alt+L in the reader, and a row in every episode context
menu) opens **Links in These Notes**: a list with one row per link, in the
order they appear, each row reading as *title, then where it goes* -- "Support
the show on Patreon, patreon.com" -- so the title is what you arrow through and
the address is there when you want it. Duplicate addresses are folded into one
row. Under the list, four buttons and the same four on the row's context menu:

- **Open in Browser** (Enter on a row): opens it and says "Opened in your
  browser".
- **Copy Address**: the address; **Copy Title and Address** one row deeper.
- **Copy All Addresses**: every link, one per line, for pasting into a note.
- **Close** (Escape): back to the reader, on the link you were on.

The button is *visible* -- in the reader's button row, not only behind a key --
and enabled only when the notes contain a link, with its accessible name saying
how many: "Links, 7 in these notes".

**View in Browser** (Alt+B in the reader): renders the notes, as the podcast
wrote them, to a temporary page with the episode's title as its heading and the
podcast's name in the page title, and opens it in the default browser. For a
listener who prefers their browser's reading tools, or a sighted person who
wants the images the podcast embedded. The page carries no scripts and is
deleted on exit. If the episode has its own web page (the feed's `<link>`),
Open Episode Web Page is the row beside it, and About This Episode says which
is which.

**Podcast description** gets the same reader under About This Podcast, with
the podcast's website as its first link.

**Empty and stripped cases** say so: "This episode has no show notes" rather
than an empty field; notes that were only an image say "The show notes are an
image with no text -- View in Browser will show it."

Built on: the existing `show_notes_dialog.py` and "Links in These Show Notes"
(kept, grown), the `_plain_text` HTML flattening (replaced by a small
HTML-to-rich-text renderer over `wx.richtext`, shared with QUILL's own reader
where one exists), and the existing feed `<link>` field on the episode.

### 5d. Watched folders

Jeff: "we need watch folders and that should be magical."

**What exists.** One `watched_folder` path per Personal Audio show; a menu row,
Scan Watched Folders (Ctrl+Alt+W), that walks each folder on the UI thread and
copies any audio file it has not seen into Cast's managed folder; one sentence
at the end with a count. Nothing watches; nothing is announced when a file
arrives; there is no window that lists the folders; and the only way to create
one is through Add Personal Audio.

**What magical means here.** You point Cast at the folder your voice recorder
syncs to, or the one your browser downloads into, or a Dropbox folder somebody
else drops lectures in -- once -- and from then on anything that lands there is
in Personal Audio before you go looking for it, announced once, never twice,
never a duplicate, and the original file is exactly where it was. You never
press Scan again. The wonder removed: "did it see the file?"

**The Watched Folders window** (Podcasts > Watched Folders..., Ctrl+Alt+W now
opens it; a peer window in the Window menu):

    Watched Folders (3)
      Voice Memos    C:\Users\jeff\Dropbox\Voice Memos    watching   14 files   last new: 2 hours ago
      Lectures       D:\Lectures                           watching   62 files   last new: Tuesday
      Downloads      C:\Users\jeff\Downloads               paused      -         --
    [Add Folder...] [Folder Settings...] [Scan Now] [Pause / Resume] [Remove...] [Close]

Each row reads name, path, state, count, last arrival. Enter opens the
folder's episodes in Personal Audio. The Applications key offers the buttons
plus Open Folder in Explorer and Copy Path. **Add Folder** is a folder chooser
followed by one page of settings; **Remove** asks, and says what survives: the
files already imported stay in Personal Audio, the folder is simply no longer
watched, and nothing on disk is touched.

**Per-folder settings** (the page behind Add Folder and Folder Settings; each
row also a Preferences default under *Data*):

- **Name** -- what Personal Audio calls the group; defaults to the folder's
  name.
- **Include subfolders** -- on by default.
- **Each subfolder is its own group** -- off by default; on, a folder of
  audiobooks becomes one group per book, in Personal Audio's own Groups
  chooser.
- **File types** -- the audio extensions Cast plays, all on by default; a
  listener can switch off, say, `.wav` to leave raw recordings alone.
- **What to do with the original** -- *Leave it where it is* (default; Cast
  keeps its own copy, as today), *Move it into Cast's folder*, or *Play it
  from where it is* (no copy; the file is referenced, and if the drive goes
  away the episode reads Unavailable and keeps its position -- the rule
  Personal Audio already follows).
- **New arrivals** -- *Add to Personal Audio* (default), *and add to the queue*,
  *and play now if nothing is playing*.
- **Tell me** -- *Once per arrival* (default: "New in Voice Memos: Tuesday
  meeting, 42 minutes"), *Once per batch* ("3 new recordings in Lectures"),
  *Quietly* (the notification record only, no speech). Always a notification
  record; the setting chooses the sound on top.
- **Ignore files smaller than** -- 30 seconds by default, so a recorder's
  accidental two-second file does not become an episode.
- **Speed** -- this group's own default, since a lecture folder and an
  audiobook folder want different speeds (R12 already gives each file its own).

**Live watching**, not scanning. Cast subscribes to the folder with the
operating system's directory-change notification (`wx.FileSystemWatcher`,
which wraps `ReadDirectoryChangesW`), so a file arriving is seen within a
second of the write finishing. Because a file that is still being written is
the classic trap -- a recorder writing a two-hour file over ten minutes -- an
arrival is *settled* only when its size has been stable for five seconds and
it can be opened for reading; until then it is "arriving", and nothing is
copied or announced. A full scan still runs at launch and on resume from sleep,
because notifications are missed while the app is closed. Scan Now stays for
the folder on a network drive, where change notifications are unreliable, and
that folder's row says "checked every 10 minutes" instead of "watching".

**Never twice.** A file is recognised by content hash, not name (R10 already):
the same recording renamed, or dropped into two watched folders, is one
episode, and the second sighting is skipped silently. A file *removed* from
the folder does not remove the episode -- the folder is a door in, not a
mirror -- unless the folder's setting is *Play it from where it is*, in which
case the episode reads Unavailable.

**When something is wrong**, the row says it and it is spoken once: "Voice
Memos is unavailable -- the drive is not connected. Still watching." A folder
that cannot be read because of permissions says so and offers Open Folder in
Explorer. Every failure lands in Recent Problems with the folder's name.

**In Personal Audio**, watched-folder arrivals are marked with their group,
and the Groups chooser (a combo, flat, like Settings for This Podcast's
categories) narrows the list to one folder's files. The Inbox can be told to
include Personal Audio arrivals (a Preferences switch, off by default), for a
listener who triages everything in one place.

Built on: `local_import.scan_watched_folder` and `_staged_copy` (kept, moved
off the UI thread onto the task manager), `local_duplicates` (the hash),
`local_import_guard` (room, verify, discard), `personal_audio` (the collection,
Unavailable, orphans), `wx.FileSystemWatcher` for the live half, and the shared
notification store for the record. The per-folder record is a new
`WatchedFolder` dataclass in the library file, replacing the one string on the
show, with a migration that turns each existing `watched_folder` into a
`WatchedFolder` with the defaults above -- so nobody's folder stops being
watched on upgrade.

### 5e. Refreshing: when Cast looks for new episodes

Jeff: "we need richer refresh podcast intervals both globally and per podcast
so that the user has far more control."

**What exists.** One global switch and one global interval from eight fixed
rows (manual, 15 and 30 minutes, 1, 3, 6, 12 hours, daily -- `refresh_policy`),
a per-podcast `check_interval_minutes` that overrides it (0 inherits), a
per-podcast `refresh_on_launch`, and the shared last-check stamp so Radio and
Cast never ask one publisher twice. Manual is the shipped default. The check
never gives up on a failing feed and never starts downloads by itself.

**What "far more control" means.** A *schedule* per podcast, not only an
interval -- because a daily news show, a weekly interview and a podcast that
publishes at 6 a.m. on Tuesdays want three different answers, and "every 3
hours" is the wrong answer to all three.

Every schedule below exists at two levels: **the default for every podcast**
(Preferences > Fetching) and **this podcast** (Settings for This Podcast >
Fetching, "Use shared default" beside it). A folder can set it for every
podcast inside. The schedule kinds:

| Kind | Settings | Reads as |
|---|---|---|
| **Manually only** | -- | "Never checks on its own." |
| **Every so often** | any number of minutes, hours or days -- typed, not chosen from eight rows; the eight stay as quick picks | "Every 45 minutes." |
| **At set times** | one to six times of day, each a time; optional days of the week | "At 6:00 and 18:00, weekdays." |
| **Around when it usually publishes** | learned: Cast keeps the day-of-week and hour each of the last twelve episodes arrived, and checks every 15 minutes in the two hours around the usual time, hourly for the rest of that day, and daily otherwise. The learned pattern is shown in words and can be pinned or reset. | "Usually Tuesdays about 6 a.m.; checking closely then." |
| **Follow the publisher's hint** | when the feed declares `<sy:updateFrequency>`/`updatePeriod` or a Podcasting 2.0 `podcast:updateFrequency`, use it | "The publisher says weekly on Mondays." |

Plus, at both levels: **check on launch** and **on resume from sleep**
(yes/no); **not during Quiet Hours** (on by default); **not on a metered
connection** (the existing switch, applied here too); and a **burst after a
miss** -- if a scheduled check was missed because Cast was closed, check once
on the next launch regardless.

**Seeing it.** Feed Check (section 6) gains two columns, *Schedule* and *Next
check*, so "when will it look again?" is a row, not a guess; the podcast's
context menu gains *Check Now* and *Change Schedule...*; a Preferences row
shows the total ("40 podcasts: 31 on the default hourly schedule, 6 learned, 3
manual") so a listener can tell at a glance what the app is doing to their
connection. The status bar's Inbox cell menu gains Refresh All Now.

**What it says.** A scheduled check speaks only when something arrived, as
today; a manual Check Now always answers, with the count or with "nothing
new". A schedule change is confirmed in the same words the table uses: "The
Daily now checks at 6:00 and 18:00, weekdays."

**Built on**: `refresh_policy` (grows a `Schedule` type with the five kinds and
a `next_due(now, last_checked, history)` function, pure and tested against a
fixed clock), `check_state` (already records when each feed last carried
something new -- the learning uses exactly that), `show_policy.cadence_minutes`
(becomes `show_policy.next_due`), the monitor (`PodcastCheckMonitor` asks
`next_due` per podcast instead of one cadence), and the existing per-podcast
fields, which migrate: an interval becomes an *Every so often* schedule,
`refresh_on_launch` becomes the launch switch, and nobody's checking changes on
upgrade.

### 6. Every other window, and what it becomes

Three dispositions. **Peer** -- a modeless window with the menu bar, in the
Window menu, Radio's way. **Dialog** -- a genuine question, modal, one purpose,
Escape cancels. **Absorbed** -- its content lives somewhere in sections 4 or 5
and the window is deleted. **Gone** -- deleted outright.

| Window | Today | Becomes | Notes |
|---|---|---|---|
| Podcast Manager | the second app | **Gone** | Sections 2.1, 4. Its episode list, filter row, sort row, boost chooser, and every button move to the main window, View and Episode menus, and the context menus. |
| Add Podcast | dialog | **Peer** | Search a directory by name; add by address; the results list with Following column, Follow/Unfollow, Preview, context menu (done). Import OPML moves to the Podcasts menu (A). Stays open while you add several. |
| Feed Preview | dialog | **Dialog** | "Is this the one?" -- a question. Follow / Cancel. Done (Phase 0). |
| Search Everywhere | dialog | **Absorbed** into Find (4.2). | |
| Play Queue | dialog | **Absorbed** into the Play Queue place (4.4); the queue-run and group actions become context-menu rows and Episode-menu rows. | Ctrl+Shift+Q goes to the place. |
| Downloads | dialog | **Absorbed** into the Downloads place. Pause/Resume All stay in the Downloads menu. | |
| Feed Check | dialog (new) | **Peer** | As built: worst first, Retry, Retry All Failed, Copy Feed Address, context menu. |
| Listening Statistics | dialog | **Peer** | The report text; Year in Review one key away. |
| Year in Review | dialog | **Peer** | |
| Continue Listening | dialog | **Absorbed** into the place. | |
| Show Notes | dialog | **Peer**, as the Notes reader (5c): rich text with headings and links, Find, Copy, the Links button, View in Browser. In Now Playing for the playing episode; its own window for any other. | |
| Links in These Notes | dialog | **Dialog**, grown (5c): title-then-address rows, Open in Browser, Copy Address, Copy All, Close. Reached from the visible Links button and the episode context menu. | |
| Episode Notes | dialog | **Absorbed** into Now Playing's note field for the playing episode; **Dialog** for any other. | |
| About This Episode (Episode Extras) | dialog | **Peer** | Season/number, people, soundbites, alternate audio, location, the Playing-from line, the feed's scheme note. |
| Chapters | dialog | **Absorbed** into Now Playing's chapters list. | |
| Chapter Review | dialog | **Dialog** | Accept/Skip inferred chapters -- a question per row. Kept. |
| Transcript | window | **Peer** | Read-along; Find inside it; Export. |
| Settings for This Podcast | dialog | **Peer** | The category chooser stays a combo box -- it is a flat list of categories, which is what Jeff observed; a tree would be wrong for it. The per-podcast page is reviewable while the library is open. |
| Podcast Settings (library-wide defaults) | dialog | **Absorbed** into Preferences as grouped, scrolling sections. | Section 13. It is the one window that does not fit on a screen (6b item 7), and its forty rows are the same rows Settings for This Podcast overrides. |
| Preferences | dialog | **Dialog** | The app's own preferences: launch place, close action, tray, keys, update check, dialog transitions, feed timer, Now Playing switch. Done (Phase 1). |
| Customize Features | dialog | **Dialog** | The shared one. Done. |
| Single Setting | dialog | **Dialog** | One number, from a context menu (Quick Actions). Kept. |
| Skip Settings | dialog | **Absorbed** into Preferences (Playing group); per-podcast overrides through Settings for This Podcast like every other row. | Four spin controls on their own menu row and their own window (6b). |
| New Folder / Rename Folder prompts | six raw `TextEntryDialog` sites | **Merged** into one `folder_name_prompt`, through `apply_modal_ids`, announcing its surface, used by the tree, the picker, the Manager's successor and the actions module alike. | Six copies, none through the dialog contract (6b). |
| Episode Filters | dialog | **Peer** | Rules per podcast; reached from Settings for This Podcast. |
| Episode Filter Rule | dialog | **Dialog** | One rule. |
| Smart Playlist Rules | dialog | **Peer** | Playlists become a Places row when any exist ("Playlists (2)"), between Favorites and Personal Audio; their rules window is a peer. |
| Show List Editor (playlist membership) | dialog | **Dialog** | Pick podcasts for a playlist. |
| Folder Picker | dialog | **Dialog** | "Move to which folder?" -- a question. Labelled tree (done). |
| Folder Settings | dialog | **Absorbed** into Settings for This Podcast, applied to a folder (the same page, heading "for every podcast in News"). | |
| Delete Folder | dialog | **Dialog** | Names what survives (podcasts step out to the top level). Done. |
| Move Shows | dialog | **Absorbed**: multi-select in the tree plus Move to Folder... in the context menu. | |
| Inbox Folder chooser | dialog (new) | **Dialog** | Kept as built. |
| Mark All as Played confirm | dialog | **Dialog** | Names the count. |
| Close confirm | dialog | **Dialog** | Exit / Minimize to tray / remember. |
| OPML Import | dialog | **Dialog** | File chooser then a review list with counts; Follow selected. (A) |
| OPML Import Report | dialog | **Dialog** | What was followed, what was already followed, what failed. (A) |
| Feed Credentials | dialog | **Dialog** | Username and password for a private feed. |
| Directory Credentials | dialog | **Dialog** | Podcast Index key. (A) |
| Quick Actions | dialog | **Dialog** | Reorder the row actions. (A) |
| Choose Columns | dialog | **Dialog** | Per list. (A) |
| Sleep Timer | dialog | **Dialog** | Type a number of minutes; the readout and the two quick actions live in Now Playing and the status bar. |
| Sound Enhancements | dialog | **Peer** | Equaliser, boost, mono, ducking -- reviewable while playing. |
| Audio Output Device | dialog | **Dialog** | A list. |
| Add Personal Audio (file chooser + duplicate question) | dialog | **Dialog** | The duplicate question names both files (done). |
| Watched Folders | one menu row and a synchronous scan | **Peer** (5d): a window listing every watched folder with its state, live watching through the operating system's change notification, per-folder settings, arrivals announced once and never imported twice. | The one string on the show becomes a `WatchedFolder` record, migrated. |
| Export Audio | dialog | **Dialog** | Format and destination. |
| Share | dialog | **Dialog** | The sentence and the link, Copy. |
| Backup / Restore | dialogs | **Dialog** | (A) |
| Export My Data / Delete All Podcast Data | dialogs | **Dialog** | (A) Delete names everything it destroys and requires typing DELETE. |
| First Run | dialog | **Dialog** | Section 14. |
| Tutorials | window | **Peer** | As today. |
| Go To | popup | **Popup** | The one key for every place; teaches the direct keys. |
| Command Palette | popup | **Popup** | Shared. |
| Keyboard Shortcuts / Global Hotkeys / Recent Problems / Quiet Hours / Export-Import Setup / Data Folder / About / Check for Updates | dialogs | **Dialog** | Shared with the family; unchanged. |
| Player Information | dialog | **Absorbed** into About This Episode and the Now Playing "Playing from" line. | |
| Speed chooser (Manager) | control | **Absorbed** into Now Playing. | |

Every peer window: menu bar installed, registered in the Window menu, transport
keys folded into its accelerator table, Escape or Ctrl+W closes it and returns
focus to the window it came from with a spoken "Closed <title>" (the shared
`announce_surface_exit`). Every dialog: `apply_modal_ids`, Enter is the
affirmative and it is named for what it does ("Follow", "Move", "Delete
Folder"), never "OK".

### 6b. What the survey found

A read-only survey of all 43 of Cast's surfaces was run against the principles
on 2026-09-30 (its full report is in the session scratchpad,
`cast-window-survey.md`, and its per-window facts are folded into the table
above). Its twenty ranked findings, each with where it is fixed:

| # | Finding | Principle | Fixed in |
|---|---|---|---|
| 1 | `set_accessible_name` is inert on Windows for buttons, so the Phase 1 "Play what?" fix is inaudible: the button still says "Play". | P3 | Phase 1: the object goes in the label (4.5). |
| 2 | "&Pause" reclaims Alt+P from the Podcasts menu the moment anything plays; GATE-15 read only the static "Pla&y". | P5 | Phase 1: Pau&se / Re&sume; the gate reads `transport_intent.button_label`. |
| 3 | Shift+F10 on the main library tree opens nothing -- only the mouse event is bound, though the tree's own help teaches the key. Radio fixed the same thing on 2026-08-16. | P6, P9 | Phase 1: bind `EVT_CONTEXT_MENU`. |
| 4 | Preview's failure still goes to a StaticText and speaks nothing, three lines under a comment describing that exact bug. | P4 | Phase 1: announce it. |
| 5 | The Play Queue has no row menu at all, though its docstring promises one. | P6 | Phase 2 (the queue becomes a place with the shared episode menu). |
| 6 | 17 of Cast's 21 lists and trees bind no keyboard context menu. | P6 | Phase 2 for the lists that survive; the P6 gate lands with it. |
| 7 | Podcast Settings calls `Fit()` over forty unscrolled rows and does not fit a 1080p screen; OK and Cancel fall off the bottom. | Visual | Phase 5: merged into Preferences, which scrolls. |
| 8 | Four duplicate mnemonics in the Manager's 21-row podcast menu (D, F, M, P); GATE-14 is blind to them because the labels pass through a local helper. | P5 | Phase 2: the menu is rebuilt for the tree (section 7); GATE-14 is taught the helper. |
| 9 | The main tree's context menu still says "&Unsubscribe...". | P7 | Phase 1. |
| 10 | Preview's affirmative button says "&Subscribe" -- the last thing pressed before a podcast is added. | P7 | Phase 1: "&Follow". |
| 11 | The Manager sets focus nowhere; "Episode List..." lands on a filter combo. | P3 | Phase 2 deletes the Manager. |
| 12 | Twenty-six silent status-label changes, including "Search failed" and "Could not follow". | P4 | Phase 3, `say_status`. |
| 13 | About thirty controls in Podcast Settings carry a help paragraph as `SetName` beside a real label -- inert on Windows, and on macOS it replaces the short label with a sentence. | P3 | Phase 5, with the merge. |
| 14 | Show Notes' rich view is an unnamed `HtmlWindow`; the preceding label was consumed by the plain view. | P11 | Phase 1 (Notes reader, 5c). |
| 15 | Smart Playlist Rules builds one checkbox per podcast -- 1,300 Tab stops on the library the app is designed for; any `&` in a title becomes a stray mnemonic. | Visual, P5 | Phase 5: the house pattern, a chooser with a reorderable list. |
| 16 | Seven mnemonic collisions between Podcast Settings and its Chapters group; GATE-14 scopes them as different classes. | P5 | Phase 5, with the merge; GATE-14 learns composed groups. |
| 17 | Live combo boxes still say "Unplayed", "All shows", "Sort shows:", "View cross-show lists as:". | P7 | Phase 5 wordlist sweep. |
| 18 | Three "&OK" buttons carry an access key, each on a letter that would resolve a collision in the same window. | GATE-14 | Phase 1. |
| 19 | A button labelled exactly "Follow" means "revert to the shared default" -- one per overridden row, all announcing the same word, now colliding with the new Follow verb. | P7, P3 | Phase 1: "Use shared default"; "Follow the Shared Defaults" likewise. |
| 20 | The OPML feed check swallows its failure and reports zero feeds checked rather than "the check failed". | P4 | Phase 3. |

Beyond the twenty: the survey confirms Cast builds **no `wx.Frame` of its own**
-- every surface is a modal dialog -- which is the whole of P9's gap and why
Phase 4 exists; six separate "New Folder / Rename Folder" text prompts, none
through `apply_modal_ids`, none announcing their surface, which become one
(Phase 2); Volume Boost has three controls for one value (Podcast Settings, the
Manager's combo, the status bar), which becomes one; the "more" and "view" rows
in the tree redirect to the Manager with "Select it there", which is the exact
behaviour P2 ends; eight windows land focus on a filter or a chooser rather
than on the thing the listener opened them for (Downloads, Feed Check, Show
Notes, Statistics, Year in Review among them), each a one-line `SetFocus`
(Phase 1); and the Play Queue opens through `show_modal_dialog` with no title
and no announce callback (Phase 1).

### 7. Context menus

The Applications key and Shift+F10 open the same menu everywhere; right-click
opens it too. Every menu is the complete verb set for that kind of thing, in the
same order every time, with rows that do not apply **disabled and not absent**,
so the menu's shape is learnable. Every row shows its key where it has one.

**A podcast** (in Podcasts, Favorites, Find): Play Next Unheard · Add All Unheard
to Queue · Mark All as Played... · (sep) · Settings for This Podcast... · Add to
/ Remove from Favorites · Move to Folder... · Rename Podcast... · (sep) · Refresh
Now · Feed Check for This Podcast · Copy Feed Address · Open Website · (sep) ·
Unfollow...

**An episode** (in any episode list, the tree, Find): Play · Add to Queue · Play
Next (top of queue) · (sep) · Mark as Played / Unplayed · Keep This Episode ·
Download / Remove Download · Refresh Episode Audio... · (sep) · Remove from
Inbox · File to Inbox Folder... · Remove from Queue · (sep) · About This
Episode... · Show Notes... · Transcript... · Add Note... · Share... · Copy Link
· Export Audio... · (sep) · Delete This Copy (Personal Audio only)

**A folder**: New Folder Inside... · Rename... · Move to Folder... · Settings for
Every Podcast in This Folder... · Mark All as Played... · (sep) · Delete Folder...

**A place** (in the Places list): its whole-place actions (4.3).

**A queue row** adds: Move to Top · Move Up · Move Down · Move to Bottom · Sort
Selected by Date · Shuffle Selected.

**A search result** (Add Podcast): Follow / Stop Following · Preview... · Copy
Feed Address · Copy Website Address · Open Website. (Done.)

**A status-bar cell**: its own actions (4.6). (Done.)

Gate P6 asserts every list binds `EVT_CONTEXT_MENU`; a snapshot test asserts each
menu's row order so a reshuffle is a reviewed change.

### 8. Keyboard

Three layers, and a listener never has to know which one a key is in:

1. **Navigation keys belong to the control.** Arrows, Home, End, Page keys, Space
   in a list, Enter, Escape, Tab, F6, Applications. The transport never eats
   them (fixed today; tested).
2. **The transport keys work everywhere in the window**, focus or not: Ctrl+P,
   Ctrl+., Ctrl+Left/Right, Ctrl+Up/Down, Ctrl+Shift+Up/Down, Ctrl+Alt+Left/Right,
   and the optional Winamp letters (Z X C V B, L, J, T) which are off in text
   fields and never claim an arrow in a tree or list.
3. **The menu keys open menus**: Alt+P, V, E, D, Q, W, H. No control in the
   window shares any of them (GATE-15).

Region keys: F6 to the status bar and back; Ctrl+F to Find; Ctrl+1 the library;
Ctrl+2 Now Playing; Ctrl+3..9 the other open windows; Ctrl+Tab cycles.

Global hotkeys (work with the window in the background): Play/Pause, Stop,
Next in Queue, Continue Listening, Refresh All -- the last three added, which is
what makes a Windows jump list unnecessary (ear.md R7).

**Go To is Ctrl+G** (Jeff asked; it already is -- Cast took it on 2026-09-30
because Radio's Go To is Ctrl+G and places are what Ctrl+G is for). Ctrl+G
opens the popup that lists every place with its direct key, so it teaches the
listener out of needing it.

**Every key is the listener's** (Jeff: "we need the ability to change hotkeys
like radio/quill/quill lite"). Cast already has both editors -- Help >
Keyboard Shortcuts (the family's `KeymapEditorMixin`, scoped to Cast's
commands, with the same conflict check and the same per-command reset) and
Help > Global Hotkeys (the allowlisted system-wide table). Phase 0 wrongly
filed both under Advanced; they are everyday rows again, in Simple mode, in
Help, where Radio and QUILL Lite keep them. Three rules follow: every command
this plan adds -- Find, the places, Now Playing, Copy Notes, Check Now, the
schedule rows, bookmarks, time remaining, Ctrl+Home -- is registered with a
command id so it appears in the editor and can be rebound; every menu label
goes through `_menu_label`, so a rebound key shows in the menu; and the
Keyboard Shortcuts Sheet is generated from the live bindings, so it cannot go
stale. A rebinding that collides with a navigation key or a top-level menu
letter is refused in the editor with the reason, which is GATE-15's rule
applied at the moment it matters.

### 9. User flows

Each flow is written as what the listener does and hears. Every sentence in
quotes is what is spoken.

**First launch.** The window opens on Podcasts, which is empty and offers three
rows. The First Run dialog (section 14) has asked one question -- "Where would you
like to land each time?" -- and offered to add a first podcast. Enter on "Add a
Podcast by Name" opens Add Podcast with focus in the name field: "Podcast name,
edit." Type, Enter: "12 results from Apple Podcasts and Podcast Index." Arrow:
"The Daily, The New York Times, Following" -- no, not yet: "The Daily, The New
York Times." Enter previews: "Previewing The Daily: 1,842 episodes, latest
Thursday's episode." Follow: "Now following The Daily; 3 back-catalogue episodes
queued for download." Escape closes Add Podcast: "Closed Add Podcast." Focus
returns to Podcasts, on The Daily.

**An evening's listening.** Launch lands on the Inbox: "Inbox, 12 episodes,
list. Thursday's episode, The Daily, 31 minutes, New." Enter: "Playing Thursday's
episode." The Now Playing line fills; focus stays. Ctrl+2: Now Playing opens,
focus on the position slider: "Position, 0:04 of 31:50." Down-arrow to the
chapters: Enter on chapter 2 -- "The main story." Ctrl+Shift+Up twice: "Speed
1.5x for The Daily." Ctrl+Alt+T, type 45, Enter: "Sleep timer set, 45 minutes."
Alt+Tab away. Forty-four minutes later: "Sleep timer, one minute left." Then
playback fades and stops; the place is saved.

**Triage.** Inbox, arrow down. Space on three rows: "Added to queue" ×3 -- no:
Space announces nothing on a single row (the list's own selection change is
enough); after a multi-select Space says "3 added to the queue." Delete on a row:
the row vanishes, the next row reads; nothing is spoken for one, "4 removed from
the Inbox" for four. Applications key on a row, R: "Remove from Inbox." Ctrl+O:
"Inbox showing News: 5 episodes."

**A broken podcast.** Ctrl+Shift+C: "Feed Check. 40 podcasts, 1 failing and 2
gone quiet. Worst first." The list: "The Daily, Failing, 3 checks in a row, Cast
is still trying, last checked 2 hours ago, last new episode 4 days ago." Enter:
"Checking The Daily." A moment later, the row re-reads: "The Daily, OK, last
checked just now, last new episode just now." Or it does not, and the
Applications key offers Copy Feed Address so the listener can look at what the
publisher is sending.

**Your own audio.** Podcasts > Add Personal Audio: a file chooser. "Lecture 3.m4a
is already in Personal Audio as Lecture Three. Add it anyway, or cancel?" Cancel.
Or Add: "Copying Lecture 3. 45 MB." "Added Lecture 3 to Personal Audio." It is
in the Personal Audio place; it plays at its own speed; deleting Cast's copy
never touches the original, and the question says so.

**Moving computers.** Preferences > Data Folder: choose a synced folder. On the
other computer the same choice; the library, positions and notes are there.
Listening Places sync carries the place to Earshot on the phone.

**Undo.** Anything destructive -- Unfollow, Delete Folder, Remove Download, Mark
All as Played, Clear Queue -- is one Ctrl+Z step, and the announcement that
follows the action says so: "No longer following The Daily. Ctrl+Z puts it
back."

**Search.** Ctrl+F, type "bristol": (pause) "14 matches for bristol." Arrow:
"Bristol bus boycott, an episode of Witness History, in BBC." Enter: the episode
is selected in New Episodes; Space queues it; Escape returns to the Inbox where
the listener was.

**Going quiet.** Help > Quiet Hours: the shared window; during quiet hours nothing
is announced that is not the result of a key the listener pressed.

**Something went wrong.** A download fails: "Episode 412 could not be downloaded:
the server said not found. It is in Recent Problems, with Retry." Recent
Problems, Ctrl+Alt+Shift+P, lists it; Enter retries.

### 10. What is spoken, and when

The rule is GATE-13's, restated for this app:

- **Never** the name of a focused control, a window title, a focus move, a
  selection change in a list, or the text of a control that just got focus. The
  reader says those.
- **Always** the outcome of an action ("Now following The Daily"), a state change
  on something unfocused ("Sleep timer, one minute left"), a background result
  ("2 new episodes from The Daily"), a count the listener cannot see ("4 removed
  from the Inbox"), and a refusal with its reason ("Nothing is selected that can
  be played...").
- **Once**, not per keystroke: Find speaks its count when typing pauses; a
  multi-select action speaks its count once.
- **A status line is spoken when it changes**, through `say_status`, which sets
  the label and speaks it. A bare `SetLabel` on a status control is a gate
  failure (P4).
- **A background failure is spoken and recorded** in Recent Problems, through
  one helper; an `on_failure` that only logs is a gate failure.
- **Nothing during Quiet Hours** that is not the direct result of a key press.

### 11. Visual design

For the sighted listener, and for the sighted person sitting next to the blind
one. Native Windows controls, system colours only, so high-contrast themes and
the Windows text-size setting just work.

- **Spacing**: 8px window gutters, 6px between controls in a row, 12px between
  groups. One rule, applied by two sizer helpers, so no window is cramped.
- **Hierarchy**: the Now Playing line in a larger weight; pane headings in bold;
  everything else in the system font.
- **Groups**: every set of controls under a heading or a `StaticBox`, so the
  window reads as regions with names -- which is also what a screen reader's
  region navigation wants.
- **Lists**: no icons (a word per row for a reader, nothing for the eye); zebra
  striping off (it fights high-contrast); column widths saved per list.
- **Buttons**: the same width within a row; the affirmative first; Close last and
  without a mnemonic.
- **Minimum size**: the window never shrinks below the point where the button row
  wraps; the panes split at a saved ratio with a keyboard-movable sash (F8 to
  the sash, arrows to move it, as QUILL's own Reveal Codes pane does).
- **Focus**: the focused control's rectangle is the system focus ring; nothing
  custom-draws focus.
- **Empty and loading**: an empty pane shows its sentence as a row, not as a
  greyed message; a loading pane shows "Loading..." as a row, replaced in place.

### 12. Words

Follow, unfollow, following. Podcast, never show or feed or subscription (except
"OPML subscription list", the format's own name). Episode. Unheard, never
unplayed or new-as-a-noun. Place. Now Playing. Find, never search. Personal
Audio. Inbox. Queue. Downloaded, never cached. Settings for This Podcast;
Defaults for Every Podcast; Preferences. Sleep timer. Chapters. Show notes; your
note. Playing from.

Every question dialog: the thing's title, what happens, what survives, then the
verb as the affirmative button. Every announcement: object first, then what
happened to it. Numbers spelled as numbers; plurals spelled out, never "(s)".

Gate P7 reads every string literal in `quill/ui/podcasts` and `quill/apps/podcasts*`
against the forbidden list, with a reviewed allowlist.

### 13. Settings

Four windows today call themselves settings, and the survey (6b) laid them
side by side: Podcast Settings holds about forty library-wide defaults and
does not fit on a screen; Preferences holds nine app settings; Settings for
This Podcast holds one podcast's overrides of the forty plus four of its own;
Skip Settings is four spin controls on their own menu row. One question --
"what happens when I open Cast" -- is split across two of them
(`default_launch_view` in Podcast Settings, `resume_on_launch` in
Preferences); "how eagerly does Cast fetch" is split across two; the Inbox
routing question is asked as a checkbox in one and a choice in another; and
Volume Boost has three controls for one value.

Two windows after this:

- **Preferences** (Ctrl+,): everything that is not about one podcast. The
  shared dialog already supports grouped sections, so it grows them: *When
  Cast opens* (launch place, resume last episode, update check); *Playing*
  (speed default, skip distances, volume boost, Winamp keys, Now Playing
  switch, sound enhancements defaults, copy notes as: plain / plain with
  links / Markdown / formatted); *Fetching* (the default schedule from 5e --
  kind, times, learn-from-the-feed -- plus check on launch and on resume, not
  in Quiet Hours, not on a metered connection, the burst-after-a-miss rule,
  auto-download count, storage cap, retention, and the one-line summary of
  what every podcast is doing); *The Inbox*
  (mode, caps); *Chapters* (the seven); *Telling you* (alert mode, digest,
  dialog transitions); *The window* (close action, tray, Alt+F4); *Data*
  (data folder, download location, sync, backups). Podcast Settings and Skip
  Settings are absorbed here, each row exactly once, and the window scrolls.
- **Settings for This Podcast** (Ctrl+Alt+,): one podcast, by category, the
  combo box kept, every row an override of the Preferences default with "Use
  the shared default" beside it -- **never** "Follow", which now means
  something else (6b, item 19). Applied to a folder from the folder's context
  menu, the same page with a different heading; Folder Settings and Watched
  Folders are absorbed as categories. Reached from the podcast's context menu
  and the Podcasts menu, not only through a window that no longer exists.

Every setting is documented (GATE-SETDOC) and has help at construction
(GATE-CAST-HELP); the vocabulary audit knows every field.

### 14. Help, the first hour, and the documents

- **F1 everywhere** (GATE-CAST-HELP): every window has an authored purpose in
  `surface_help`, every control an inline `SetHelpText`. The two new windows
  (Feed Check, the main panel's buttons) are the current failures and are fixed
  in Phase 1's commit.
- **First Run** asks one question, "Where would you like to land each time?"
  with the four choices from Preferences, and offers "Add your first podcast" as
  a button. Everything else it used to say moves to the Tutorials.
- **Tutorials** (Ctrl+Alt+F1) are rewritten against the new shape: The first
  hour; Places; Find; Now Playing; The Inbox; The Queue; Your own audio; Keys;
  Sleep and speed; When something breaks. Each lesson's checks (`tutorial_checks`)
  are updated to the new names.
- **The documents** -- user guide, release notes, announcement, changelog, PRD --
  are rewritten against sections 4 to 9 of this plan, in Phase 6, and rendered
  through the shared accessible template.

### 15. Phases, and what is done

Each phase is shippable on its own, ends in a commit, and leaves the gates green.
Ordered by listener impact divided by risk.

#### Phase 0 -- landed 2026-09-30, committed as `ba69898` and the commit after it

Unlabelled fields; Preview; Follow/Unfollow with state and undo from every
surface; context menu on results; arrows returned to the tree; the Play button
names its object; the Manager's combo boxes named; GATE-CTLLABEL (165 found, may
only fall); Simple/Advanced; Customize Features; the View menu; the status bar;
the Window menu; Feed Check; Remove from Inbox; the Inbox folder scope; the three
Shortcuts verbs; Refresh Episode Audio; the Community menu removed; Follow
vocabulary.

#### Phase 1 -- stop the bleeding

Built and lint-clean, 2,741 tests passing, **committed as `fef27b3` on 2026-10-01** and re-verified against the source the same day:

- [x] GATE-15 and the two collisions it found (Alt+S, Alt+V).
- [x] Pinned views open: Inbox, New Episodes, Continue Listening, Favorites.
- [x] Play understands an episode and a view.
- [x] Podcasts / Episode / Downloads / View / [Quillins] / Window / Help;
      Quillins Advanced-only. (The source appends View after Downloads; the
      plan's section 4.7 order with View second is still the target and moves
      with Phase 2's menu rebuild.)
- [x] Unfollow beside Add, named after the selection.
- [x] "Open Manager" is "Episode List..." until Phase 2 deletes it (the button;
      the Podcasts menu row still reads "Open Podcast Manager..." and goes with
      the Manager in Phase 2).
- [x] Launch lands on what is new.
- [x] The remaining 15 Cast controls labelled (146 left tree-wide, none in Cast).
- [x] The Manager's duplicate unfollow collapsed onto the shared undoable one.

Forced by the survey (6b), each a small certain fix. **Re-verified 2026-10-01:
none of these had landed** -- `set_accessible_name` still targets every main
panel button, `transport_intent.button_label` still returns `&Pause` (Alt+P
against the Podcasts menu), the main tree binds only `EVT_TREE_ITEM_MENU`,
the tree menu still says "&Unsubscribe...", Preview still says "&Subscribe",
the three "&OK" buttons and "Follow &the Shared Defaults" are unchanged,
`global_hotkeys` and `keymap_editor` are still in `ADVANCED_ROWS`, and none of
the five dialogs calls `SetFocus`. They are the active worklist, in this order
(the first landed with X-06 on 2026-10-01 and is struck below):

- [x] The button row carries its object in the **label**, not the accessible
      name (6b item 1); Pau&se and Re&sume; GATE-15 reads
      `transport_intent.label_samples` (item 2); a gate that no
      `set_accessible_name` targets a `wx.Button` in Cast. Done 2026-10-01
      with X-06, through the shared `core/transport_button.py`.
- [x] `EVT_CONTEXT_MENU` on the main library tree, so Shift+F10 opens the row
      menu its own help promises (item 3). Done 2026-10-01.
- [x] Preview's failure is spoken (item 4); the OPML feed-check failure is
      spoken (item 20). Done 2026-10-01.
- [x] "&Unsubscribe..." in the tree menu, "&Subscribe" in Preview, "Subscribe
      to ACB Media" in the Podcasts menu, "Subscribe using this feed URL",
      "When I unsubscribe" in Podcast Settings, "Unsubscribe them too" in
      Delete Folder: all Follow (items 9, 10). Done 2026-10-01.
- [x] The per-row "Follow" revert button and "Follow the Shared Defaults" become
      "Use shared default" (item 19). Done 2026-10-01.
- [x] The three "&OK" buttons lose their access keys (item 18). Done 2026-10-01.
- [x] Keyboard Shortcuts and Global Hotkeys come out of `ADVANCED_ROWS` and
      back into Help in Simple mode (section 8), done 2026-10-01: every key is the listener's,
      and Radio and QUILL Lite keep the editors in plain sight.
- [x] Focus lands on the thing the window is for: Downloads, Feed Check, Show
      Notes, Statistics, Year in Review each gain one `SetFocus` (done
      2026-10-01); the Play Queue
      passes its title and announce callback to `show_modal_dialog`.
- [x] The Show Notes rich view gets its label back (item 14) -- or is replaced
      outright by the Notes reader (5c), whichever lands first. Label done
      2026-10-01; the Notes reader stays with Now Playing.

Written but not yet applied (the extraction script exists; two supporting pieces
were mid-flight when Jeff said stop). Re-verified 2026-10-01: `launch_place.py`
exists and nothing imports it; `podcasts_preferences.py` does not exist;
`PodcastHistory.switch_to_now_playing` does not exist; there are no tests for
`library_tree.py`; GATE-15 **is** on the `platform_report` roster; the two
tests **were** updated in `fef27b3`; `labelled_field.py` still takes `help=`;
no Find field and no Now Playing surface exist:

- [x] Preferences extracted to `podcasts_preferences.py` with two new rows:
      Where to land on launch; Switch to Now Playing when playback starts.
      Needs `PodcastHistory.switch_to_now_playing` and `core/podcasts/launch_place.py`
      (the latter is written). Extraction and the launch row done 2026-10-01; the
      Now Playing switch moved into the Now Playing row.
- [x] Tests for `library_tree.py`; GATE-15 on the `platform_report` roster.
      Done 2026-10-01 (the roster in `fef27b3`).
- [x] Two tests to update to the new truth (`test_add_podcast_focus_return`,
      `test_podcast_show_actions_credentials`), and `surface_help` purposes for
      Feed Check and the main panel's new buttons (GATE-CAST-HELP). Done
      2026-10-01 (the tests in `fef27b3`).
- [x] `labelled_field.py`: drop its `help=` parameter -- help set inside a helper
      is invisible to the help audit, so callers set it inline. Done 2026-10-01.
- Find in library above the tree (the interim of P10).
- Now Playing (section 5), with the Notes reader and the grown Links
      dialog (5c) as its show-notes pane -- the reader is built once here and
      the Show Notes peer window in Phase 4 reuses it.
- Commit.

#### Phase 2 -- one window (P1, P2, P10)

The Places list, the content pane and Find, as in section 4, hosted by a
`MainViewHost`-shaped `wx.Simplebook`: each place is built lazily, retained while
the window is open, and refreshed when its model changes. Showing a place is a
view transition, not a second copy of the library or a new dialog. The Manager's
episode list and its actions move to the main window; its filter and sort rows
become View-menu items; the five Manager mixins are re-homed on the frame;
`manager_dialog.py` and the Manager's own Search Everywhere are deleted.
GATE-REACH and the help audit name anything left behind. Every reveal path
points at the new panes.

With it, because they are the same window: the Places customisation (4.3:
reorder, hide, rename, the chooser, `places_layout`); Notifications as a place,
a status-bar cell and a peer window with per-notice actions (5b); the complete
feature-switch inventory (17), because every place and cell has to be absent
when its switch is off, and building the list without the switches would mean
building it twice. Two or three sessions; the largest change in the plan and
the one that makes the rest cohere.

#### Phase 3 -- nothing silent (P4)

`say_status`; the sweep of every `_status.SetLabel`; the banned-pattern rule;
background failures through one helper into Recent Problems; then the per-window
audit: open each surface, press each button, write down what was heard.

#### Phase 4 -- every surface a peer (P9)

The "Peer" rows of section 6, through the shared `peer_window` contract and
Radio's `_show` pattern. Each surface has one opener that can summon a
modeless window or embed the same panel in the primary window; opening an
already-created peer raises it and refreshes it instead of creating a duplicate.
Escape and Ctrl+W close it, return focus to the initiating control, and use the
shared exit announcement. With it, **Watched Folders** (5d) in full: the window, the `WatchedFolder` record and its
migration, the scan moved off the UI thread, live watching through
`wx.FileSystemWatcher` with the settled-file rule, per-folder settings, the
Groups chooser in Personal Audio, and arrivals announced once through the
notification store. It is scheduled here rather than earlier because its
window is the first peer window built from scratch rather than converted, and
it is a good one to set the pattern with: one list, one row of buttons, one
context menu, nothing modal.

#### Phase 5 -- names, words, settings, schedules (P7, sections 12, 13, 5e)

The wordlist gate and its sweep; the settings consolidation into two windows;
and, because it lives in the same two windows, **refresh schedules** (5e): the
`Schedule` type and `next_due`, the monitor asking per podcast, the learned
publish-time kind, the publisher's-hint kind, the migration from the three
existing fields, the Feed Check columns, Check Now and Change Schedule in the
podcast menu. Every menu row read aloud once by somebody who did not write it.

#### Phase 6 -- the first hour (section 14)

First Run; Tutorials; the five documents; the F1 audit.

#### Phase 7 -- the extensions (section 18)

In the order they earn their keep: time remaining on one key (3) and Ctrl+Home
(5), which are an afternoon each; bookmarks (1) and timestamp links (2), which
share the seek plumbing Now Playing builds; up next (4); earcons through the
shared feedback setting (7); Play this next (9); follow from the clipboard (8);
the global hotkey for Now Playing (11); undo history, shared with Radio (12);
the braille status line, through QUILL's layer (6); the per-podcast note (10)
lands with whichever AI feature first reads it.

#### After that

ChatGPT connectivity through the shared adapter (ear.md A1); the text-only AI
features (A2 onward), each behind its own switch in section 17; the remaining
Earshot parity items (ear.md R8-R10, B1-B3).

### 17. Every feature has a switch

Jeff: "all features should be configurable to turn them on or off."

Customize Features today has eight areas. It becomes the complete inventory
below: every capability Cast has, grouped, each a checkbox, each on by default
(only an explicit off is stored, so a feature added later is on for everybody
until they say otherwise -- the rule `app_features.py` already follows). A
switched-off feature is **absent**: its place is not in the Places list, its
rows are not in the menus, its cell is not in the status bar, its keys do
nothing, and its window is not in Go To. The palette still lists its command
with "(off in Customize Features)" so a listener who remembers the name learns
where it went. Profiles at the top -- Everything, Just Listen (places, Now
Playing, sleep timer, nothing else), Earshot-like -- set the boxes and then the
boxes are the truth.

| Group | Switches |
|---|---|
| Places | Inbox · New Episodes · Continue Listening · Favorites · Personal Audio · Play Queue · Downloads · Playlists · Notifications |
| Playing | Now Playing window · Chapters · Chapter inference · Transcripts · Show notes · Your notes · Bookmarks (18) · Sleep timer · Speed controls · Sound Enhancements · Skip silence · Intro/outro skip · Audio output device · Winamp keys · Scan hold · Global hotkeys · Stop after this episode |
| Library | Folders · Custom order · Find · Feed Check · Episode filters · Smart playlists · Quick Actions · Choose Columns · Hide caught-up · Inbox folders and caps · Inbox folder scope · Watched folders |
| Getting podcasts | Directory search · Add by address · Follow ACB Media · OPML import/export · Private feeds (credentials) · Podcast Index credentials |
| Keeping things | Downloads · Auto-download · Retention · Housekeeping · Free up space · Keep this episode · Refresh Episode Audio · Backup and restore · Export my data |
| Telling you | Notifications window · Toasts · Sounds (earcons) · New-episode digest · Feed failure notices · Gone-quiet notices · Feed check timer · Dialog transition announcements |
| Listening data | Statistics · Streaks · Year in Review · Recently played · Listening Places sync · Data folder sync |
| Around the app | Status bar · Window menu · Tray · Tutorials · Command Palette · Go To · Share · Export audio · Quillins · Advanced mode · ChatGPT connectivity (later) · AI features (later, each its own switch) |

Each switch is an `AppArea` with a label and a one-line why; the gate that
makes this exhaustive is a test asserting every command id in Cast's palette
maps to exactly one area, so a new command cannot arrive without a switch.

### 18. Extensions -- what Cast should gain, not only fix

Jeff: "if you think we need to extend features/windows/controls/hotkeys/
behavior then do so." These are the additions I would make. Each names the
wonder it removes. None is a Phase 1 or 2 item; each is scheduled in section 15.

1. **Bookmarks in an episode.** Ctrl+B marks the current position with an
   optional one-line note; a Bookmarks list in Now Playing and in About This
   Episode; Enter jumps. Earshot's Quick Action; Cast has notes but not places
   in an episode. Removes: "where was that bit?"
2. **Timestamps in show notes are links.** Show notes routinely contain
   "12:34 -- the interview". In the notes field, Enter on a timestamp seeks
   there. Removes: reading a timestamp and then typing it into Go to Position.
3. **Time remaining on one key.** Ctrl+Shift+T speaks "12:04 of 31:50, 19
   minutes left" and, if a sleep timer is running, "sleep in 33 minutes".
   Radio's What's Playing key, applied to time. Removes: opening Now Playing to
   learn whether the episode fits the drive.
4. **Up next, spoken before it happens.** Ten seconds before an episode ends
   with more in the run: "Next: Episode 412 from Accidental Tech Podcast."
   Configurable; off in Quiet Hours. Removes: the jolt of a new voice with no
   warning.
5. **Ctrl+Home is home.** From anywhere in the window, Ctrl+Home returns to the
   launch place with focus on its first row. Removes: "how do I get back?"
6. **A braille status line.** The Now Playing line and the last announcement
   pushed to a braille display's status region, through QUILL's existing
   braille layer (family rule 10: QUILL has it, Cast reaches it). Removes: a
   deaf-blind listener having nothing at all.
7. **Earcons for the four outcomes.** A short sound for added-to-queue,
   removed, done, and failed, from QUILL's sound scheme, under the shared
   `action_feedback` setting (sound / speech / both / silent). Removes: waiting
   for a sentence to learn that a one-key action worked.
8. **Follow from anywhere.** Ctrl+N with a podcast's address on the clipboard
   pre-fills Add Podcast and previews it. Removes: the copy-switch-paste dance.
9. **"Play from the top of the queue" is Play Queue's Enter**, and "Play this
   next" (top of queue) is Shift+Space on any episode. Removes: a three-step
   reorder to hear one thing next.
10. **A per-podcast "what I care about" note** for the later AI features to
    read, editable now in Settings for This Podcast, so the data exists before
    the feature does. Removes nothing yet; costs nothing now.
11. **Global hotkey for Now Playing.** Bring the console to the front from any
    app. Removes: Alt+Tab through everything to find the one window with the
    slider.
12. **Undo history.** Help > Undo Last already restores the last destructive
    act; a small list of the last ten, each with its own Undo, for the case
    where the mistake was three actions ago. Shared with Radio.

### 19. What Radio has, and Cast should

A direct source comparison of Radio's main shell, player, browse, status-bar,
peer-window and shared-menu surfaces gives Cast a set of implementation
patterns, not just a list of features to imitate. The rule is to reuse the
contracts and shared controllers; Cast must not grow a second playback engine,
command router, window registry or announcement vocabulary.

#### 19.1 Host the library like Radio hosts its views

Use the Radio `MainViewHost` shape: a small host owns a `wx.Simplebook`, a
stable page id for each place, and the transition from the Places list to the
current content page. Page builders are lazy and persistent. A page is built
once, retains its list state and column choices while the window is open, and
gets an explicit refresh when its model changes. The host owns visibility and
focus landing; pages do not hide one another by reaching into the frame.

The useful division is:

- the Places model decides order, visibility, labels and counts;
- the host decides which page is shown and calls `focus_current()`;
- the page decides how its rows are rendered and which shared context menu it
  needs;
- the command/controller layer performs the action and reports its outcome.

That boundary keeps a place switch cheap, makes Ctrl+Home and Ctrl+G reliable,
and prevents the deleted Manager from reappearing as hidden navigation state.
It also makes feature switches honest: an off place has no page, menu rows,
status cell or direct key, rather than a page that is merely visually hidden.

#### 19.2 One surface, three dispositions

Radio's player and browse surfaces establish the seam Cast needs for Now
Playing, Add Podcast, Notes, Feed Check and Watched Folders. Each substantial
surface should expose the same small lifecycle:

1. `build(parent, ...)` constructs the controls once.
2. `embed_in(host)` places that panel in the primary `Simplebook` or another
  named region.
3. `summon(owner, ...)` opens or raises the modeless peer using the same panel
  contract.
4. `refresh_open()` updates an already-visible surface without rebuilding its
  controls or stealing focus.
5. `focus_default_control()` lands on the thing the surface is for.

The opener accepts `embed_in` where embedding is valid; it does not fork into
an embedded implementation and a peer implementation. Now Playing therefore
has one player panel and one transport/controller path: it can live in the
main window, be summoned as a peer, and remain the single source for position,
chapters, speed, sleep and notes. A true question remains a dialog; a review
surface remains a peer; an absorbed surface is not kept alive behind the
primary window.

#### 19.3 Commands and menus have one owner

Every action is a command id with one callable implementation. Keys, menu rows,
buttons, context-menu rows, status-bar cells and the Command Palette dispatch
that id; they do not call different private handlers that happen to do the
same thing. Use Radio's shared surface-menu installation and Window menu so a
peer receives the same transport commands, rebinding labels and close path as
the primary window. A menu label is generated from the live keymap, and a
disabled command remains visible when the verb does not apply to the current
selection.

This is especially important for queue and playback mutations. The queue
controller, download controller and player controller own the state change;
the UI surface supplies selection and focus context, then consumes one result
for speech, sound, undo and Recent Problems. No context menu or toolbar button
gets a private shortcut to persistence.

#### 19.4 The status bar is a navigable surface

Cast's status bar should follow Radio's F6-only contract: it is a compact,
interactive summary, not another tab stop between every button. F6 enters it,
Left/Right moves between stable action cells, Enter performs the selected cell,
and F6 returns to the prior control. Cells expose the current object and state
in their visible label, own their context menu, and refresh in place. A changed
unfocused cell goes through `say_status` and the shared feedback policy; focus
movement itself is left to the screen reader.

This gives the listener one predictable route to volume, speed, queue, Inbox,
downloads, sleep and time without duplicating those controls in the main
content pane. It also makes the status bar a useful fallback when a feature
page is switched off.

#### 19.5 Focus, lifetime and announcements are part of the contract

Opening a surface records the initiating control. The surface chooses an
explicit default focus target, Escape/Ctrl+W closes it, and focus returns to
the initiator or the nearest surviving row. Reopening a peer raises the same
instance. Closing the primary window destroys embedded pages and unregisters
peer surfaces; no timer, watcher or controller may retain a dead widget.

The app speaks outcomes and background changes, never titles, focus moves or
the text a focused control already exposes. Use the shared transition and exit
helpers, and test both modeless and embedded paths. The acceptance test for a
new surface should cover: open from a key, open from a menu, open from a row
menu, default focus, Escape, Ctrl+W, close with pending work, reopen, and focus
return.

#### 19.6 What to copy, and what not to copy

Copy Radio's host, lazy-page, player-panel, peer-window, status-bar,
Window-menu, focus and announcement contracts. Do not copy Radio-specific
domain names, playback policy, tray assumptions or a second implementation of
anything Cast already shares with QUILL. The test for parity is not visual
similarity: the same user action should reach the same shared primitive and
produce the same kind of truthful outcome.

The remaining product ideas from the comparison are still worthwhile: a
What's Playing-style time-remaining command, a useful tray menu, flattened
Find results, and the shared update/install flow. They belong in the extension
roadmap only after the host and surface contracts above are in place.

### 20. The tree, right now

Read this before the next session does anything.

- **HEAD is `ba69898`** (the Add Podcast fixes). The large Phase 0 commit after
  it was attempted twice and the pre-commit hook failed both times -- first on an
  unregistered dialog (since registered), then in its own stash rollback
  ("unable to unlink old tests/unit/core/speech/test_voice_conversation.py").
  The working tree was verified intact after the second failure; nothing was
  lost. The commit has not landed.
- **About 130 files are modified or new and uncommitted.** They are Phase 0
  and Phase 1 above, plus the **Audio Description removal**, which is
  **partially applied**: the agent doing it was killed by the session's API
  limit (2026-09-30, resets 2 p.m. Phoenix) after staging the deletions (12
  files: `quill/core/adp/`, `adp_dialog.py`, `main_frame_adp.py`,
  `_adp_client_key.py`, the two ADP tests, the acceptance docs) and editing
  the callers in `radio.py`, `studio.py`, `weather.py`, `main_frame*.py`,
  `features.py`, `feature_catalog.py`, `settings.py`, `unlock_codes.py`,
  `network_egress_entries.py` and `.gitignore`. All four apps still import.
  Its last report: eight remaining test failures, all source-text assertions
  against files it was mid-edit on. Unknown: whether every snapshot was
  regenerated (`surface_reachability`, `dialog_inventory`,
  `settings_vocabulary`, `main_frame_public_surface`, `settings_doc`,
  `accessible_name`), and whether `git grep -in "adp\b"` is clean. Radio's
  Community menu was to be kept for Ask QUILL Radio and the ACB schedule --
  verify it was.
- **The whole-app window survey finished** and is merged (6b). **The Radio
  survey did not run** (19).
- **The commit message is written** at the scratchpad's `commit_msg.txt`.
  Committing needs, in order: finish the ADP removal (re-run its seven checks;
  regenerate the snapshots; fix or delete the eight assertions); update the
  two stale Cast tests (`test_add_podcast_focus_return`,
  `test_podcast_show_actions_credentials`); add `surface_help` purposes for
  Feed Check and the main panel's new buttons; `ruff format .`, `ruff check .`,
  GATE-11, GATE-14, GATE-15, `platform_report`, then `pytest tests/unit -q`;
  then `git add` of the Cast paths and the ADP paths, and the commit. The
  pre-commit hook's stash-and-rollback has failed once on this tree; if it
  does again, commit the two halves (Cast, ADP) separately rather than
  bypassing the hook.
- **Two scratchpad scripts are written and not yet run**, both for Phase 1:
  `extract_prefs.py` (moves Preferences to `podcasts_preferences.py` and adds
  the launch-place and Now-Playing rows; needs `PodcastHistory.
  switch_to_now_playing`, not yet added) and the GATE-15 roster entry. Their
  supporting core module, `core/podcasts/launch_place.py`, is written.
- `ear.md` is still the Earshot-parity worklist and has not had its completed
  items purged (Jeff asked for that earlier today; it is queued behind this
  plan).

### 21. Technical notes

The decisions an implementer needs that the design sections do not state.

#### 21.1 Data model changes, and the one rule about them

Every new field defaults to what the old behaviour was, so an upgrade changes
nobody's app; every stored enum is read through a normaliser that maps junk to
the safe answer; nothing is ever renamed on disk. In order of appearance:

| Where | Field | Default | Notes |
|---|---|---|---|
| `PodcastHistory` (`history.py`) | `menu_mode`, `show_status_bar`, `hide_caught_up` | `simple`, `True`, `False` | done |
| `PodcastHistory` | `switch_to_now_playing` | `False` | Phase 1; the extraction script expects it |
| `PodcastSettings` (`models_settings.py`) | `inbox_folder_scope` | the ALL sentinel | done; `models_settings.py` is at 586 of 600 lines -- the next field extracts something first |
| `PodcastSettings` | `default_launch_view` | `""` (automatic) | exists; exposed in Phase 1 |
| `PodcastLibrary` (`subscriptions.py`) | `places_layout: list[PlaceRow]` (id, shown, custom name) | the section 4.3 order, all shown | Phase 2; travels with a synced data folder because it is in the library file |
| `PodcastLibrary` | `watched_folders: list[WatchedFolder]` | migrated from each show's `watched_folder` string | Phase 4; the string stays readable for one release, then is dropped |
| `PodcastSettings` and per-show overrides | `refresh_schedule: Schedule` | migrated from `check_interval_minutes` / `refresh_minutes` / `refresh_on_launch` | Phase 5 |
| `PodcastEpisode` (`models_episode.py`) | `bookmarks: list[Bookmark]` (ms, note) | `[]`, serialised only when non-empty | Phase 7 |
| `PodcastShow` | `display_name` | `""` (feed title wins) | ear.md R8; `models.py` is at 270 of 270 -- extract `PodcastFolder` to `models_folder.py` first |
| `AppFeatureSettings` (`app_features.py`) | the section 17 areas | all on | Phase 2 |

#### 21.2 New modules, by phase, and where the size budget bites

GATE-11 is a ratchet. These modules are at their ceiling and take nothing new:
`apps/podcasts.py` (1039), `core/podcasts/models.py` (270),
`ui/podcasts/player_controller.py` (609), `ui/podcasts/manager_dialog.py`
(1238, and it is deleted in Phase 2). Anything that would grow them goes in a
new module; today's extractions (`main_panel.py`, `places.py`,
`podcasts_view_menu.py`, `manager_lookups.py`) are the pattern.

- Phase 1: `apps/podcasts_preferences.py` (written by script);
  `core/podcasts/launch_place.py` (written); `ui/podcasts/now_playing.py` +
  `now_playing_cells.py` if it passes 600; `ui/podcasts/notes_reader.py`
  (`wx.richtext` over a small HTML-to-rich converter) +
  `core/podcasts/notes_export.py` (the four copy formats, pure);
  `ui/podcasts/find_box.py` (interim Find over the tree).
- Phase 2: `ui/podcasts/main_view_host.py` (the Cast `Simplebook` host),
  `ui/podcasts/places_list.py`, `content_pane.py`,
  `episode_list.py` (the Manager's list, extracted), `core/podcasts/places.py`
  (the layout model), `core/podcasts/find.py` (the one search core; ranking is
  pure and tested), `ui/podcasts/context_menus.py` (the section 7 menus,
  one builder per kind, order snapshot-tested), `ui/podcasts/folder_prompt.py`
  (the one prompt).
- Phase 3: `ui/podcasts/say_status.py`; a `failure_report` helper beside it.
- Phase 4: `ui/podcasts/peer_window.py` (Cast's `_show`, calling Radio's
  shape), `ui/podcasts/surface_menu.py` (the shared peer menu/window wiring),
  `ui/podcasts/watched_folders_window.py`,
  `core/podcasts/watched_folders.py` (the record, the settled-file rule, pure).
- Phase 5: `core/podcasts/refresh_schedule.py` (`Schedule`, `next_due`),
  `core/podcasts/words.py` (the wordlist), the Preferences groups.
- Phase 7: `core/podcasts/bookmarks.py`, `core/podcasts/notes_links.py`
  (timestamp and link extraction, pure).

#### 21.3 Gates to add, each small

- **GATE-15** exists; extend it to read `transport_intent.button_label`
  outputs and, later, the places-list and content-pane labels.
- **No `set_accessible_name` on a `wx.Button`** in Cast (AST, one file).
- **GATE-14 through helpers**: teach `check_access_keys` the Manager's
  `action(...)` helper and the settings catalogue's labels; today both are
  invisible to it (6b items 8, 16).
- **P6**: every `ListCtrl`/`TreeCtrl`/`ListBox` in `quill/ui/podcasts` binds
  `EVT_CONTEXT_MENU`; a snapshot of each context menu's row order.
- **P4**: banned pattern for `._status.SetLabel(` outside `say_status`; and
  for an `on_failure=` lambda that does not call the failure helper.
- **P7**: the wordlist test with its allowlist.
- **P2**: any tree or list row whose label matches `\(\d+` has children or
  content.
- **Feature switches**: every palette command id maps to exactly one area.
- **Hosted pages**: every enabled place has one stable page id, is built lazily
  at most once per primary window, and refreshes without replacing the focused
  control; switching places never creates a dialog or a second data model.
- **Shared dispatch**: every key, menu, button, context-menu and status-cell
  action resolves to one command id and one implementation; a test exercises
  each route for the queue and playback mutations.
- **Peer lifecycle**: every peer has an opener, a default focus target, an
  initiating-control focus return, Escape/Ctrl+W close behavior, and duplicate
  open prevention. Embedded and modeless paths use the same panel builder.
- **Migration**: removing the Manager includes a one-release reader for old
  settings and persisted Places/watched-folder state, a backup before rewrite,
  an idempotent migration test, and a rollback/error announcement that leaves
  the original data recoverable.
- **Release documentation**: the user guide, tutorials, keyboard sheet,
  dialogs checklist, release notes and stale Manager references are checked by
  a search gate before Phase 6 closes.
- **GATE-CAST-HELP** and **GATE-CTLLABEL** as they are; the `labelled_field`
  helper must stop taking `help=` (help set inside a helper is invisible to
  the help audit -- found by the labels agent).

#### 21.4 Threading and the watcher

Everything that touches the network or the disk for longer than a keystroke
runs on `QuillTaskManager` and answers on the UI thread through
`wx.CallAfter`, as Cast's downloads and refresh already do. New work that must
move there: the watched-folder scan (today synchronous on the UI thread), the
notes-to-browser render, Find over transcripts (indexed once per transcript on
first search, cached beside it). `wx.FileSystemWatcher` delivers on the UI
thread; the settled-file check (size stable five seconds, openable) runs on a
timer, and the copy it triggers goes to the task manager. A watched folder on
a network path falls back to a ten-minute timer, because `ReadDirectoryChangesW`
over SMB is unreliable.

#### 21.5 Windows facts this plan depends on

- A button's accessible name is its label; `set_accessible_name` is inert for
  it (`accessible_names.py`). Text fields, combos, lists and trees take their
  name from the `StaticText` created immediately before them, in creation
  order, not sizer order.
- An ambiguous Alt+letter goes to the control, not the menu bar (GATE-15's
  reason).
- Windows routes Alt+arrow to the menu system before a tree sees it, so
  Alt+Shift+Up/Down is caught in the frame's `EVT_CHAR_HOOK`, as Radio does.
- `wx.MessageBox` does not announce the dialog it opened; `show_message_box`
  does. Every question goes through the latter.
- `SetHelpText` stores nothing without a `wx.HelpProvider`;
  `ensure_help_provider()` runs at activation.
- Formatted copy is `CF_HTML` (with the required header block) plus an RTF
  flavour on the same clipboard object; `wx.DataObjectComposite` carries both.
- The Winamp letters live on the frame's char hook and pass through when a
  text field, a tree or a list has focus and the key is one that control
  navigates with (done; tested).

#### 21.6 Performance constraints

The library the app is designed around is 1,300 podcasts and about 196,000
episodes (`_reload_library_tree`'s comment). Consequences: the content pane's
episode list is virtual (`wx.LC_VIRTUAL`) and asks the model per row; the
places' counts are computed once per redraw, not per row; Find ranks lazily
and stops at 500 matches with "and more -- narrow the search"; the folder tree
keeps its placeholder-per-podcast expansion; the Smart Playlist chooser is a
list, never a checkbox per podcast (6b item 15).

#### 21.7 Hazards met today, so the next session does not meet them again

- The Bash tool collapses `\\` inside heredocs and `-c` strings; a `"\x00"`
  written that way became a real NUL byte in `places.py` and took four gates
  down. Write patch scripts with the Write tool and run them; never put a
  backslash escape through a heredoc.
- Files are mixed CRLF/LF; every script reads and writes with `newline=""`
  and detects the file's own ending.
- Replacing "the last method in a file" by slicing to end-of-file deleted five
  module-level helpers once; anchor on the next `def` or on end-of-class.
- The pre-commit hook scans the whole tree, so a concurrent agent's oversized
  file blocks everyone's commits; and its stash-and-rollback can fail on a
  busy tree. Commit in halves rather than bypass it.
- Two agents editing `manager_dialog.py` at once briefly produced a file with
  the class defined twice. One writer per file.

## Family Reliability Review

Original document title: QUILL QC2: the whole family, made dependable.

| | |
|---|---|
| Status | Remaining work after the QC pass. Completed changes and validation are in the Completed Changes and Validation section below. |
| Date | 2026-09-30 |
| Scope | QUILL, Quill Radio, Quill Cast, QUILL Lite, shared core, UI, I/O, stability, documentation, tests, and release gates. |
| Purpose | Find bugs, design risks, performance traps, accessibility gaps, and UX improvements before they become another user study. |
| Companion | The Cast Product and UX Plan section is the detailed Cast redesign. This document is the wider quality and product review. |

### 0. How to read this

This is deliberately more disciplined than a wish list. Every item carries one of
these confidence labels:

- **Confirmed** means the behavior or structural condition is visible in the
  current source tree.
- **Confirmed user report** means the source documents the problem as an actual
  observed behavior, even if a partial mitigation now exists.
- **Conditional risk** means the source has no direct failure proof, but the
  current ownership or shutdown contract leaves a credible failure path.
- **Recommendation** means a product or architecture improvement, not a claim
  that the current implementation is broken.
- **Existing strength** means a pattern worth protecting and reusing.

Priority has two dimensions. **P0** is an acceptance blocker when the condition
is present: silent data loss, an inaccessible primary workflow, focus theft, or
an operation that cannot be cancelled or recovered. **P1** is a high-risk fix
for the next quality pass. **P2** is important architecture, performance, or
UX work. **P3** is polish after the contracts are sound.

Accessibility is not a separate section at the end. In this memo, accessibility
means that the user can perceive the state, understand what happened, operate
it from the keyboard, keep their place, recover from failure, and use speech,
braille, visual, and earcon output without one channel contradicting another.

### 1. Executive assessment

QUILL has unusually good accessibility infrastructure for a growing desktop
product. The shared `AppShellFrame`, dialog contract, F1 help engine, keymap
labels, announcement rules, braille and earcon support, tray handling, and
Radio's reviewable Now Playing field are the right foundations. The strongest
next step is to make those foundations the ownership boundary for every
background operation and every app surface.

The main risk is not a missing button. It is that a background result, a timer,
a close request, a settings write, or a focus restoration can outlive the
surface that owns it. The user then gets one of four bad experiences:

1. nothing is said;
2. something is said after it is no longer relevant;
3. focus lands in a container instead of the thing they can use; or
4. the app quietly accepts a change that was never persisted.

The next quality pass should therefore prioritize these five contracts:

1. **Every operation has an owner and a lifetime.**
2. **Every outcome has a structured, accessible result.**
3. **Every close path is idempotent and observable without blocking exit.**
4. **Every focus move has a remembered origin and a safe return target.**
5. **Every expensive read, parse, search, or download can report progress and
   be cancelled without leaving a half-updated model.**

The broad review found no reason to throw away the current architecture. It did
find several places where the architecture is expressed by convention rather
than by a shared contract. Those are the places most likely to regress as the
family grows.

### 2. Findings at a glance

| ID | Priority | Confidence | Area | Finding |
|---|---:|---|---|---|
| F-01 | P2 | Remaining UX integration | Lite settings | Failure feedback, dirty state, truthful Preferences results, and retry are implemented. Direct Retry/Open Settings Folder activity controls and broader writer adoption remain. |
| F-02 | P1 | Remaining adoption | Background work | Adopt the implemented lifetime token in short-lived surfaces using shared managers; add reviewable activity retention. Manager shutdown already suppresses queued and late delivery. |
| F-04 | P1 | Remaining code and acceptance | Lite focus | Bounded activation repair is implemented. Unsuccessful-repair diagnostics, justified family-helper adoption, and manual acceptance remain. |
| F-05 | P1 | Confirmed | Lite performance | `DocumentFrame.load()` reads and decodes plain and rich files synchronously on the UI path. A size warning does not make the actual read non-blocking. |
| F-06 | P1 | Confirmed | Shutdown | Radio and Cast intentionally swallow most teardown and final-save exceptions. This protects exit, but it also hides cleanup failures and can make the next session inherit stale or incomplete state. |
| F-08 | P2 | Confirmed | Maintainability | `quill/ui/main_frame.py` is still about 19,254 lines, with Radio at about 2,295 lines and Cast at about 939 lines. The extraction direction is right, but the remaining ownership surface is too large for safe change. |
| F-09 | P2 | Recommendation | Cast performance | The planned whole-library search, transcript search, feed refresh, and download state need an incremental index and bounded background work before they become a UI scan. |
| F-10 | P2 | Recommendation | Cross-app UX | QUILL has shared mechanisms for announcements, help, dialogs, menus, and trays, but not one shared operation/result/activity model. Similar actions can still explain success, failure, and progress differently. |
| F-11 | P2 | Recommendation | Persistence | `--new-instance` Lite windows share settings, so the documented last-writer-wins behavior can overwrite window preferences from another process. |
| F-12 | P2 | Recommendation | Release quality | Many important guarantees live in planning documents or manual sign-off lists. Convert the most important ones into behavioral or source-contract tests so a later refactor cannot quietly remove them. |

None of these findings calls for a broad rewrite. Each is best addressed at the
nearest shared boundary, then adopted by the apps.

### 3. What is already working well

#### 3.1 Shared shell and accessibility infrastructure

`quill/ui/app_shell.py` already contains several patterns that should become the
family default:

- common speech, braille, earcon, and status paths;
- F1 context help installation;
- shared modal dialog handling and modal-stack tracking;
- deferred close confirmation outside `EVT_CLOSE`;
- tray restoration and deferred tray exit;
- menu labels derived from the active keymap;
- global and media hotkey registration with guarded teardown;
- shared task-manager access and app feature handling.

This is a strong base. QC2 should extend it rather than have each app invent a
second lifecycle framework.

#### 3.2 Radio's reviewable Now Playing field

`quill/apps/radio_now_playing.py` is a model for accessible dynamic text:

- the field is a read-only multiline `wx.TextCtrl`, not an unreviewable label;
- updates are skipped when the text is unchanged;
- updates are deferred while the field has focus;
- elapsed position is available on demand instead of being rewritten every
  second;
- the status bar remains a separate scan surface.

Cast should use the same rule for episode title, podcast, playback state, and
position. QUILL should use the same rule for any dynamic status that a user may
need to review word by word.

#### 3.3 Recovery locking is already guarded

The current recovery callers acquire the file lock and release it in
`finally` blocks. That is not a current bug to "fix" blindly. A context manager
could make the invariant harder to forget in future code, but the immediate
quality work belongs in recovery UX and test coverage, not in changing a working
lock lifecycle without a failing case.

#### 3.4 Defensive close behavior has a reason

The broad exception handling in Radio and Cast shutdown exists so a failed tray,
hotkey, controller, or optional Quillin cleanup cannot prevent the user from
closing the app. That is a valid accessibility decision: a close command must
not turn into a frozen or permanently trapped window.

The improvement is observability, not removing the guards. Cleanup errors should
be captured in a safe diagnostic result and surfaced at the next useful moment,
while the close itself remains reliable.

### 4. P0 acceptance contracts

These are the conditions that should block a release when violated. They are
product contracts, not a claim that every one is currently failing.

#### 4.1 No silent state-changing action

If an action changes a file, setting, queue, subscription, recording, download,
playback state, feature state, or recovery state, the user gets one concise
outcome through the appropriate channels:

- the focused control's own native announcement is not duplicated;
- the app speaks only the result or a reason it could not happen;
- the result is available in braille and a reviewable status surface;
- the result includes the object and the next useful action when one exists;
- background results do not steal focus.

A generic "done" is not enough. The result should answer: **what happened,
to what, and what can I do now?**

#### 4.2 No focus theft and no focus abandonment

Every surface records the initiating control before opening a dialog, peer window,
search state, picker, or modeless panel. On success, cancellation, error, and
close, focus returns to a valid target in the originating surface unless the
user deliberately moved elsewhere.

A background refresh must never move focus. Activation repair must not steal
focus from a text field, menu, dialog, or other interactive control that the
user deliberately selected.

#### 4.3 No unbounded or un-cancellable busy state

Any operation that can take long enough for a user to wonder whether it worked
must show an accessible state with:

- operation name and current object;
- determinate progress when known, otherwise a truthful busy state;
- cancel when cancellation is safe;
- retry or recovery when it fails;
- a stable place to review the result after focus moves away.

A busy cursor, a changing label, or a silent background thread is not a
progress contract.

#### 4.4 Close always reaches a known state

Every close path must be safe when invoked by Alt+F4, the File menu, a tray menu,
Windows logoff, a peer-window close, and an already-running close request. It
must be idempotent and must distinguish:

- work that must be stopped or committed before the window disappears;
- best-effort cleanup that must not block exit;
- failures that should be recorded for the next launch.

The user should never have to guess whether a close command was ignored, vetoed,
minimized to the tray, or completed.

### 5. Detailed findings and fixes

#### F-01. Integrate settings failures with Activity/Problems

The silent-failure bug is fixed. Session values remain active, the status
message retains a dirty-state warning, Preferences reports truthfully, reopening
Preferences retries, and queued warnings are flushed before shutdown. Tested
changes are recorded in [QC3](#completed-changes-and-validation).

Done 2026-10-02. `quill/core/persistence_outcome.py` is the contract
(`guarded_write`: outcome with path and a stable reason code, a retry closure,
the `OSError` re-raised unchanged); QUILL's and QUILL Lite's settings, Radio's
and Cast's history and the podcast library write through it.
`quill/ui/persistence_reporting.py` is installed once per app and turns a
failure into an Activity result with Retry and Open Folder, spoken once per
file per minute, with the later success of the same file reported too.
Failure-injection tests: `tests/unit/core/test_activity_results.py`
(`test_a_guarded_write_reports_success_and_failure_and_still_raises`,
`test_the_real_settings_writers_report_through_the_guard`) and
`tests/unit/apps/test_lite_activity.py`. The NVDA/JAWS/Narrator check is a
manual scenario, not code.

#### F-02. Adopt lifetime guards in short-lived surfaces

The shared guard and shutdown suppression are implemented and tested; see
[completed changes](#completed-changes-and-validation). Done 2026-10-02:
the per-surface tokens, the delivery-time guard and the timer-ownership gate
shipped 2026-10-01; a terminal result that arrives after its window closed now
goes to the Activity store as a review row (`surface_lifetime._record_outlived`,
`tests/unit/ui/test_activity_window.py::test_a_result_that_outlives_its_window_goes_to_activity`)
instead of being dropped.

#### F-04. Lite activation can still lose focus

Implemented: one event-loop check and one 75 ms settling check, activation
generations, menu/visibility/shutdown guards, and intentional-focus preservation.
Deterministic event-order regressions and live wx MDI/text-control checks pass.

Remaining:

- Manual Alt+Tab cycles with NVDA, JAWS, and Narrator, including Find, menus,
  child creation and child close; confirm immediate typing and no duplicate speech.
- Extract a reusable family focus helper when a second actual caller adopts it.
- Add a diagnostic count of unsuccessful container-focus repairs without
  logging control contents or introducing announcements.

#### F-05. Lite file opening is synchronous on the UI path

**Evidence:** `quill/apps/lite_window_file.py::DocumentFrame.load()` calls
`Path.read_text()`, `Path.read_bytes()`, RTF safety scanning, and the editor load
path directly. The public load method is reached from the window-opening flow.

**Impact:** large plain-text files, slow network folders, antivirus scanning,
large RTF files, or a damaged file can make the window stop responding. A
listener cannot tell whether opening is working, and a sighted user sees a
frozen frame. A size confirmation is useful policy, but it does not solve the
latency after confirmation.

**Fix shape:** split open into a worker preparation phase and a UI commit phase:

1. capture the path and a document-open generation;
2. read, decode, and scan on the worker;
3. show an accessible busy state with the filename and Cancel when safe;
4. on the UI thread, discard a result whose generation is stale;
5. commit the decoded text or sanitized RTF atomically to the control;
6. restore document memory, language, spelling, and the caret only after the
   commit succeeds;
7. on failure, keep the original empty or previous document state and offer
   Retry, Open as Plain Text, or Leave Open.

Rich Edit control mutation must remain on the UI thread. The expensive file and
scan work does not have to.

**Tests:** a delayed reader, cancellation, open-then-close, two opens in quick
succession, malformed RTF, large-file latency budget, and focus after success
and failure.

#### F-06. Shutdown is reliable but not observable enough

**Evidence:** Radio and Cast protect optional shutdown, final stats/library
writes, controller shutdown, hotkey removal, and tray removal with broad
exception handlers. Both shut down the task manager without waiting for all
workers.

**Impact:** this is correct for the immediate close experience, but a failed
final write can be indistinguishable from a successful one. A stale recording
marker, incomplete resume state, or missing podcast library flush can then
appear as a problem on the next launch. The user receives neither a useful
explanation nor a recovery path.

**Fix shape:** add a shared shutdown report with three classes:

- **must-record:** markers, resume state, and user-owned data writes;
- **best-effort:** tray and global hotkeys, optional controllers, analytics;
- **background:** work that can finish later but can no longer touch the closed
  surface.

Each guarded action records a stable internal error code and a user-safe summary.
The close path still completes. On the next launch, the app can say one concise
sentence such as `The previous session could not finish saving playback state.`
with a Details and Retry path. Never put document content, stream URLs, or
credentials in that diagnostic record.

**Tests:** inject failures into each class, assert that close still completes,
assert that required failure state is retained, and verify the next-launch
message is spoken once and is reviewable later.

#### F-08. The largest modules still hide ownership boundaries

**Evidence:** current measured sizes are approximately:

- `quill/ui/main_frame.py`: 19,254 lines;
- `quill/apps/radio.py`: 2,295 lines;
- `quill/apps/podcasts.py`: 939 lines;
- `quill/apps/lite.py`: 595 lines.

Radio and Lite already use mixins and extracted modules, and the repository has
module-size budgets. The risk is that the main ownership class still knows too
much about commands, focus, dialogs, persistence, peers, and lifecycle.

**Impact:** large files increase the chance that a focus, menu, or shutdown fix
works in one route but misses a sibling route. They also raise review cost and
make it harder to identify which code owns a timer or callback.

**Fix shape:** extract by lifetime and invariant, not by arbitrary line count:

- document/session lifetime;
- surface/window lifetime;
- operation/task lifetime;
- persistence and recovery;
- command registration and menu rendering;
- status, announcement, braille, and earcon output;
- peer-window registry and focus return.

Every extracted module should have a narrow host protocol and a focused test.
Keep the module-size budget as a ratchet, but do not split code into thin files
that only move the ambiguity around.

### 6. App-specific review

#### 6.1 QUILL editor

##### Protect the editor surface

The native text editor is the product's strongest accessibility decision. New
features should continue to wrap the editor rather than replace it with a
custom-drawn writing surface. Every new panel, preview, assistant, or browser
must have a direct keyboard route back to the document and a deterministic focus
return.

##### Make background work feel attached to the document

AI, OCR, watch-folder work, indexing, conversion, spell checking, and external
engine operations should show an operation name, target document, current step,
and cancellation state. The result belongs in a reviewable activity history,
not only in a transient status message.

A user who returns to QUILL after a minute should be able to answer three
questions without reconstructing the past:

- Is the document safe?
- What changed?
- What can I undo or retry?

##### Keep the status bar details-on-demand

The existing status and F6 conventions are valuable. Extend them consistently:
a compact headline on the default surface, a focusable details surface, and a
single action to repeat the last important announcement. Do not turn every
background event into a speech interruption.

##### Do not let the main frame become the integration bus

The size of `main_frame.py` is a maintainability warning even where behavior is
correct. New command handlers should continue to land in feature mixins or
services, with `MainFrame` acting as composition and routing. A new feature is
not complete until its teardown, focus return, F1 help, menu label, status
result, and test are owned by the same feature boundary.

#### 6.2 Quill Radio

##### Existing strengths

Radio already demonstrates several family-level answers:

- a reviewable, guarded Now Playing field;
- a focusable status bar reached through F6;
- searchable or browsable station surfaces;
- explicit playback and recording state;
- peer windows with deliberate focus return;
- deferred close confirmation through the shared shell;
- a shared path for adding or removing the playing station from Favorites.

Keep these as shared patterns when Cast or future apps need the same behavior.

##### Make long-running radio work observable

Recording, scheduled recording, catalog refresh, weather monitoring, feed
refresh, reminders, and stream recovery can all continue while the user works
elsewhere. Each should have a single activity representation:

- state: queued, running, paused, retrying, completed, cancelled, failed;
- object: station, recording, catalog, or schedule;
- progress: determinate or explicitly indeterminate;
- next action: stop, retry, open folder, review details, or dismiss;
- output: speech/braille/status wording from the same result object.

A timer or controller callback should never be the only place that knows what
happened.

##### Keep metadata calm

Radio's now-playing update discipline is exactly right. Do not weaken it by
adding elapsed time, bitrate, or other values that rewrite the focused field.
Those facts belong in on-demand status or a details window. If metadata is
missing, say less rather than repeatedly announcing that it is missing.

##### Audit optional subsystem failures

The shutdown path intentionally protects the user from optional teardown
failures. Add failure injection tests around the controller, recorder, scheduler,
tray, hotkeys, and peer-window registry. The goal is not to show an error dialog
while closing. The goal is to prove that the next session can explain a failed
marker or incomplete write without exposing implementation details.

#### 6.3 Quill Cast

`qc.md` is the detailed Cast redesign and should remain the source of truth for
its new surface. QC2 adds the following repo-wide constraints.

##### Search must be an index, not a scan disguised as a feature

The planned single search box is excellent UX, but searching podcasts, episodes,
notes, transcripts, and folders can become an accidental full-library scan on
every pause. Build it as an incremental index:

- feed and episode changes update the affected records;
- transcript indexing is a cancellable background task;
- search results carry type, location, and state;
- the UI receives immutable result snapshots;
- an index rebuild has progress, cancellation, and a clear offline/error state;
- stale results identify themselves and cannot overwrite a newer query.

Typing must remain responsive, and the result list must announce a stable count
once per settled query rather than once per keystroke.

##### Downloads need a real job surface

A Downloads menu is not enough for a listener who cannot see a spinner. Every
item should expose state, percentage or indeterminate progress, bytes when
useful, pause/cancel/retry, destination, and the reason for failure. A failed
item must remain in a reviewable list until the user dismisses it or retries it.

The download surface should not require the user to keep the menu open. It also
must not announce every byte update. Use milestones and on-demand details.

##### Feed refresh needs per-feed truth

A single `Refresh All` result such as "done" hides partial failure. Report
success, offline, authentication, parser, and rate-limit outcomes per feed,
with a summary count. New episode discovery should not silently change the
meaning of Inbox or Favorites; the list heading and status should say when the
underlying data was refreshed.

##### Empty, loading, and offline states are product surfaces

Cast's places should remain stable even when empty. Each empty state should say
what the place is, why it is empty, and one reachable next action. Loading
should identify the object being loaded. Offline should preserve locally
available content and state what will happen when connectivity returns.

These states need keyboard focus behavior and screen-reader wording, not only
visual placeholder text.

##### Keep object names in transport actions

The action label must say `Play Thursday's episode`, `Stop The Daily`, or
`Remove The Daily from Favorites`, not only `Play`, `Stop`, or `Remove`. Radio's
shared control-label rule and Cast's `transport_intent` tests should become one
family helper where the object is known.

#### 6.4 QUILL Lite

##### Preserve the small product boundary

Lite must remain an editor-first product, not a second QUILL. The family parity
rule is valuable: a capability that Lite needs should move into shared code and
QUILL should receive the same capability when appropriate. Do not solve a Lite
problem by creating an isolated implementation that later drifts.

##### Make MDI tradeoffs explicit

The MDI design gives stable document numbers and a useful Window menu, but MDI
children do not appear in Alt+Tab. That is an intentional tradeoff, not a bug
by itself. The product should make the route obvious through:

- a predictable Window menu;
- Ctrl+Tab and Ctrl+F6 parity;
- Alt+digit routes for the first nine documents;
- a title that includes the document number;
- a first-run or F1 explanation that does not interrupt typing.

The focus repair in `lite_shell.py` still deserves the regression tests described
in F-04.

##### Make multi-instance persistence honest

`--new-instance` is useful, but two processes writing one settings file means the
last process to close can overwrite window state from the other. Options, in
increasing complexity:

1. document the scope clearly and exclude volatile window state from the shared
   settings write;
2. merge settings fields using a per-field last-modified record;
3. give each instance a session-local window-state file and merge only stable
   preferences;
4. discourage concurrent instances only when a conflicting write is detected.

Atomic writes prevent half-written JSON. They do not prevent a valid older
snapshot from replacing a valid newer snapshot.

##### Give file opening the same care as autosave

Lite already treats recovery and autosave seriously. Opening should receive the
same explicit state machine: requested, reading, decoded, committed, failed, or
cancelled. That makes the large-file fix testable and makes focus behavior
predictable.

### 7. Shared UX improvements

#### 7.1 A structured action result

Introduce a small shared result model rather than having every feature invent a
sentence at each call site. It could contain:

- `action`: save, play, follow, export, refresh, open, recover;
- `object_name`: the user-facing object;
- `outcome`: completed, blocked, cancelled, failed, partial;
- `summary`: concise sentence for status and speech;
- `reason`: why it was blocked or failed;
- `next_actions`: retry, undo, open, details, or dismiss;
- `operation_id`: correlation for logs and background tasks;
- `importance`: whether it is spoken immediately or only made reviewable.

Render the same result into speech, braille, a status cell, a visual label, and
an activity row. The wording can still be app-specific, but the information
shape should be stable.

This directly addresses the recurring user report that a button did nothing.
It also supports GATE-13: a native control announcement remains native, while
the result renderer says only what the control cannot.

#### 7.2 An accessible Activity and Problems surface

A shared Activity surface would collect active and recent operations across the
current app:

- active downloads, recordings, imports, scans, saves, and refreshes;
- completed and failed results;
- retry, cancel, undo, open destination, and details actions;
- timestamps and object names;
- bounded retention;
- no document content or secrets in the record.

This should not become a noisy notification feed. Announce important transitions
once, then make everything reviewable on demand through a list with a stable
keyboard shape.

#### 7.3 Progress as a first-class accessible control

Use one shared progress model and renderer:

- `phase`: preparing, reading, parsing, downloading, writing, finalizing;
- `current` and `total` when determinate;
- `message`: the current object and phase;
- `can_cancel`, `can_pause`, and `can_retry`;
- `last_announced_milestone` to prevent speech storms;
- `owner_token` to prevent stale delivery.

A progress dialog is only one renderer. The same operation should be visible in
an activity list and a compact status cell, so closing a dialog does not destroy
access to the result.

#### 7.4 Focus memory per surface

Every reusable surface should have a small focus record:

- initiating window and control;
- last meaningful control in the surface;
- selected object identity, not only a row index;
- return action for success, cancellation, and failure;
- whether returning focus is still safe.

This is particularly important for Cast search results, Radio peer windows,
Lite MDI children, file pickers, and QUILL side panels. Returning to a row index
after the list changed is not enough; return by stable object identity and choose
the nearest valid row when the object disappeared.

#### 7.5 Repeat last important announcement

A consistent command should repeat the last important app result, not the last
thing the screen reader already read. It should be available in QUILL, Radio,
Cast, and Lite with the same concept and different app vocabulary only where
necessary.

The stored message should be the structured result, so the app can render it in
speech, braille, and a details surface. It should not capture arbitrary document
text or credentials.

#### 7.6 A real status hierarchy

Keep three levels distinct:

1. **Immediate outcome:** one concise speech/braille announcement.
2. **Compact status:** current app state, reachable through the standard status
   route such as F6 where applicable.
3. **Details:** a reviewable window or activity row with full explanation and
   next actions.

This prevents two opposite failures: silence when the result matters, and a
constant stream of progress messages that makes the app tiring to use.

#### 7.7 Settings that answer tasks

The settings model is broad and powerful. The UX should add:

- one searchable settings view with exact labels and aliases;
- task recipes such as `Prepare for dictation`, `Quiet background work`,
  `Set up podcast downloads`, or `Make the editor high contrast`;
- a preview of changes before applying them;
- one undo action for a recipe or multi-setting change;
- a clear distinction between current session state and persisted state;
- a direct retry when a settings write fails.

A recipe must be a visible composition of existing settings, not a hidden mode
that changes unrelated behavior.

#### 7.8 Better first-run paths

First-run experiences should be task-oriented and skippable. The first screen
should answer:

- what can I do here;
- what is the first useful action;
- what key or menu reaches it;
- how do I return without losing my place.

Radio's Browse Stations route and Cast's Add Podcast route should both work
without requiring a user to understand the data model first. An empty library
should be an invitation with one primary action, not a dead list.

#### 7.9 Offline and failure states are not exceptions to UX

Every networked app needs stable wording and controls for:

- offline at startup;
- offline during refresh;
- authentication required;
- rate limited;
- partial success;
- stale local data;
- retry queued;
- permanently unsupported content.

The user should be able to continue with local content, understand what is
stale, and retry without reconstructing the original action.

#### 7.10 Feature switches must remove ambiguity

The existing feature and dispatch gates are a good foundation. A disabled
feature should:

- remove all routes that would falsely imply it is available;
- retain one discoverable explanation in Customize Features or Help;
- explain why a command is unavailable when a surface can show disabled rows;
- stop background work and polling associated with the feature;
- restore the feature without leaving stale menu items or status cells.

A feature switch that hides a button but leaves a key, palette command, timer, or
tray entry is an accessibility failure because the user cannot see the route
that still exists.

### 8. Performance plan

Performance work should measure user-visible budgets, not only function duration.
A fast worker that leaves the UI frozen or the screen reader silent is not a
fast feature.

#### 8.1 Add launch and interaction budgets

Measure cold and warm startup for QUILL, Radio, Cast, and Lite:

- process start to first usable window;
- first focusable control;
- first spoken title;
- first document or library content;
- time to open the command palette;
- time to open Settings;
- time to return focus after a peer or dialog closes.

Keep the measurements in a diagnostic mode and add a small regression threshold
for each app. Do not make the normal launch noisy.

#### 8.2 Move expensive reads off the UI thread

The Lite open path is the immediate case. The same audit should cover:

- document conversion and format parsing;
- RTF safety scans;
- podcast feed parsing and transcript indexing;
- OPML import/export and backup creation;
- catalog refresh;
- OCR and image description;
- large settings or history migration.

The UI thread should own controls and model commits. Workers should produce
immutable preparation results with a cancellation token and an owner generation.

#### 8.3 Coalesce dynamic updates

Use equality checks, debounce, and milestone reporting for:

- search queries;
- playback position;
- feed refresh counts;
- download bytes;
- catalog status;
- repeated settings changes;
- speech and braille status updates.

Never solve a speech storm by suppressing all outcomes. Preserve a reviewable
latest state and announce meaningful transitions.

#### 8.4 Bound memory and indexing

For large libraries and documents:

- index incrementally;
- cap transcript and search result memory;
- avoid retaining full duplicate strings in UI rows and model snapshots;
- paginate or virtualize where a list can grow without a practical bound;
- make cache eviction observable in diagnostics;
- keep user data out of logs.

A 50 MB document budget already exists in the core performance tests. Add
comparable budgets for Cast library search and feed refresh, and for opening a
large Lite file after the asynchronous path lands.

#### 8.5 Treat polling as a resource with a policy

Every timer should declare:

- owner and shutdown method;
- interval and reason;
- whether it runs while hidden or minimized;
- offline behavior;
- whether duplicate ticks are coalesced;
- what happens when the callback outlives the surface.

This applies to Lite's inbox, Radio's recording and monitoring timers, Cast's
feed checks, and shared update checks.

### 9. Test and gate proposals

The repository already has strong gates. QC2 should add only the gates that
protect recurring failure classes.

#### 9.1 Accessibility and focus

- **Outcome contract test:** every state-changing command returns or emits a
  result with object, outcome, and next action.
- **Focus lifetime test:** every dialog, peer, picker, search mode, and modeless
  panel has success, cancel, failure, and close focus paths.
- **No stale delivery test:** invalidated surface tokens suppress worker
  callbacks and announcements.
- **Dynamic text test:** focused reviewable fields do not rewrite under the
  reader; unchanged text is not written again.
- **Context-menu parity test:** lists and trees expose the same action set by
  keyboard, menu, and context menu where the action is applicable.
- **Feature-route test:** disabling a feature removes its menu, key, palette,
  tray, status, and background routes.
- **Screen-reader acceptance matrix:** NVDA, JAWS, and Narrator for the primary
  workflows, with speech, braille, focus, and keyboard results recorded
  separately.

#### 9.2 Lifecycle and persistence

- close while a worker is queued, running, failing, and reporting progress;
- close while a timer tick is queued;
- close twice and close through every route;
- forced OS close where the event cannot be vetoed;
- tray restore and tray exit;
- peer-window destruction and app shutdown;
- read-only settings directory and failed atomic write;
- corrupt, partial, or old settings JSON;
- two Lite instances writing settings;
- recovery offer dismissed, recovered, failed, and retried.

#### 9.3 Performance

- cold and warm startup thresholds per app;
- first usable focus threshold;
- large plain-text and RTF open;
- Cast search over a synthetic library with transcript content;
- feed refresh with slow, failing, and partial sources;
- download queue with many items;
- bounded memory under repeated search and open/close cycles.

The tests should fail on a user-visible regression, not on a machine-specific
microsecond difference.

#### 9.4 Documentation and generated references

Keep the existing generated reference gates authoritative for keybindings, F1
help, settings documentation, site links, dialog inventory, reachability, and
surface fixtures. Add a review rule for any new operation or feature:

- it appears in the user-facing help model;
- its disabled and failure states are documented;
- its keyboard route is generated or tested;
- its dialog or peer surface is inventoried;
- its manual sign-off row names the actual entry route.

Planning documents can explain intent, but they should not be the only place a
release guarantee exists.

### 10. Staged roadmap

#### Stage 1: remove silent and stale outcomes

1. Integrate settings failure actions with Activity/Problems and verify screen readers.
2. Adopt the shared UI lifetime token in short-lived surfaces and activity history.
3. Add shutdown failure capture for required writes and stale markers.
4. Add the Lite activation/focus regression matrix.
5. Add a focused large-file opening test and choose the asynchronous design.

#### Stage 2: make the shared contracts reusable

1. Introduce the structured action result.
2. Introduce the shared Activity/Problems model.
3. Introduce the progress model with cancellation and owner invalidation.
4. Introduce the focus-memory helper.
5. Standardize repeat-last-important-announcement and details-on-demand.

#### Stage 3: apply the contracts to each app

1. Complete the Cast one-window redesign from `qc.md`.
2. Give Cast downloads, feed refresh, search, and offline states the shared
   operation model.
3. Give Radio recording, scheduling, catalog, and recovery the same activity and
   failure model.
4. Move Lite open, inbox, autosave, and multi-instance persistence to explicit
   lifetime contracts.
5. Keep QUILL's editor, AI, OCR, conversion, and watch-folder work on the same
   progress and recovery primitives.

#### Stage 4: pay down ownership and performance debt

1. Extract `main_frame.py` by lifetime and invariant.
2. Reduce Radio and Cast orchestration modules without duplicating behavior.
3. Add launch, search, feed, and large-document performance budgets.
4. Make every timer declare owner, policy, and shutdown behavior.
5. Convert the most important planning promises into behavioral gates.

#### Stage 5: product delight after reliability

1. Finish searchable settings coverage: unified Preferences entry points for
  Converter, Player, and Inkwell; accessible web forms; manual screen-reader
  acceptance. Native existing Preferences search is implemented. Task recipes
  remain unimplemented.
2. Focus, review, and session profiles built from existing settings.
3. Richer queue and activity views.
4. Better first-run guidance with skippable task paths.
5. Cross-app personalization that never changes keyboard or screen-reader
   fundamentals without an explicit user choice.

### 11. Definition of truly excellent

QUILL and its companion apps will feel excellent when a listener or writer can
answer these questions without seeing the source, remembering a hidden mode, or
repeating an action in hope:

- What is focused?
- What is this control going to act on?
- Did it work?
- If it did not work, why not?
- What can I do next?
- Where did my focus go?
- Can I undo, retry, cancel, or recover?
- What is still running after I leave this window?
- What will survive closing the app?
- Can I review the answer through speech, braille, keyboard, or sight?

That is the common product language the family needs. The architecture is close:
Radio has several of the right patterns, Cast now has a coherent target shape,
Lite has a clean small-product boundary, and QUILL has the deepest shared
infrastructure. QC2's work is to turn those good local answers into explicit
lifetime, result, focus, progress, and persistence contracts that every app can
keep.

## Screen-Reader Testing Handoff

This section records user-experience changes implemented in source, not a
release announcement. Test the current source build; older installed builds
may not contain these changes. All manual checks below are pending. Automated
test passes do not mean speech, braille, native Alt+Tab, or every app was
manually verified. Do not tick a checkbox until a human completes that check.

Run the keyboard checks separately with NVDA, JAWS, and Narrator. Record the
reader/version, app/build or commit, result, and exact unexpected speech or
focus behavior under the relevant item. Repeat relevant checks with the status
bar hidden and announcement throttling enabled. Never include document content,
tokens, or credentials in the test report.

Every subsequent code change affecting UX must add or update a subsection here
with its app, entry point, keyboard sequence, expected speech/state/focus,
failure/cancel behavior, automated coverage, and remaining limitations.

### Native Preferences Search

Implemented in commit `1822e4c`. Search navigates existing controls; it does not
edit settings, press action buttons, or save the dialog.

Entry points: open the app's existing Preferences or Settings command. In QUILL
and Lite, Preferences is Control+Comma. Radio, Cast, Studio, Weather, and Beacon
use their existing Preferences/Settings menu routes. Native modal and sanctioned
modeless Settings/Preferences surfaces use the same search implementation.

- [ ] On opening, find the named **Find a setting** field by Tab; confirm its
  name and editable role are spoken once and F1 gives useful control help.
- [ ] Type a word from a setting's label or help, such as **recovery** in Lite
  or **auto sync** in Beacon. Focus must stay in the search field as results
  update. Changing the query must not change or save a setting.
- [ ] Press Down to enter **Matching settings**, then arrow through results.
  Confirm each name and selection is read naturally without duplicate app speech.
- [ ] Press Enter on a match. Its actual control receives focus, with its
  current value/state spoken by the reader. Enter in search must not trigger
  the dialog's default OK/Apply or activate an action button.
- [ ] Choose a match on a hidden notebook/book page. Confirm that page is
  revealed before focus moves. In Beacon, a Sync match must show the Sync section.
- [ ] Press Control+F from a setting. It returns to search and selects the
  current query so typing can replace it.
- [ ] Search for a nonexistent setting. Confirm zero matches is reviewable and
  no previous result remains selectable. Count speech is debounced when the
  host supplies an announcement callback; some hosts currently expose only the
  on-screen count. Record silence or duplicate count speech as an acceptance issue.
- [ ] Find a disabled setting where available. Its result identifies it as
  disabled; Enter must not enable it, edit it, or move focus to an unusable control.
- [ ] While search has text, press Escape: it clears the query and keeps the
  window open. Press Escape again with an empty query: the original window's
  cancel/close behavior applies, with no unintended save.
- [ ] Change a setting normally, return to search, then Cancel. Existing cancel
  semantics must remain intact. Repeat with OK/Apply and confirm only intentional
  settings changes are applied. Immediate-action buttons retain their authored
  behavior when deliberately activated outside search.
- [ ] Close while typing a query, then reopen. No delayed result-count speech
  should arrive from the closed window, and the replacement surface must work.
- [ ] Verify Tab/Shift+Tab order, result-list reachability, and readable sizing
  at a smaller window size and increased display scaling.

Coverage: 67 Preferences/dialog/Beacon tests, followed by 29 search/dialog
tests after modeless onboarding and 12 search/Beacon tests after helper
extraction. These include real wx controls, Lite's constructed Preferences,
Beacon's hidden Sync panel, disabled controls, and value/cancel preservation.

Limits: Converter, Player, and Inkwell do not yet have unified Preferences entry
points. Web forms and unopened nested dialogs are not indexed. QUILL's hub
search finds categories and descriptions, not controls in unopened child dialogs.
Do not report this as completed all-app/global settings search.

### Radio and Cast Transport State

The primary transport action must say what pressing it will do, **and to
what, in its visible label** (implemented 2026-10-01, X-06). Radio's
main-window contract is a single button: stopped offers "Play <selected
favorite>" (Alt+L), active offers "Stop <what is playing>" (Alt+T), and paused
offers "Resume <it>" (Alt+U); with a folder or nothing selected it reads "Play
-- nothing selected" and pressing it says what would work. Cast has a primary
"Play <selection>" / "Pause <episode>" / "Resume <episode>" button (Alt+Y,
Alt+S) plus a separate Stop (Alt+T) that is disabled when nothing is playing
or paused. The object is in the label because an accessible name on a wxMSW
button is never read. The label, enablement, and action must agree. Do not
announce a state the focused native control says. The Volume slider in Radio's
main window is now Alt+O.

Entry points: Radio's main player window and Cast's main podcast window. Test a
playable station/show, a local or recorded item, and a bounded Cast episode.

- [ ] With playback stopped and a playable target selected, Tab to the primary
  transport. It must be enabled and read "Play" followed by the name of the
  selected station/show/episode -- the name you gave a renamed favorite, in
  Radio. In Cast, separate Stop must be disabled, never an enabled dead action.
- [ ] Arrow the list to a folder (Radio), a folder, an empty show or a view
  with nothing playable (Cast). The button must read "Play -- nothing
  selected"; pressing it must say which two things would work and start
  nothing. Arrow back to a playable row: the label must follow without
  anything else being said.
- [ ] Select a podcast whose title is longer than forty characters. The label
  must end with an ellipsis and the button must not change width; Tab onward
  and confirm the buttons after it did not move. A title containing an
  ampersand must read naturally and not create a stray Alt key.
- [ ] In Cast, select a podcast: the Unfollow button must read "Unfollow" and
  that podcast's name. Select one of its episodes: the same. Select a folder:
  plain "Unfollow", disabled.
- [ ] Start playback. Radio's primary button changes to Stop; Cast's changes to
  Pause, with separate Stop available only when it can stop active playback.
- [ ] Pause a bounded Cast episode. Resume and the episode's name must be
  offered (Alt+S, the same letter Pause had) and continue at the saved
  position; no control may be mislabeled as Stop. In Radio, pause a podcast or
  recording with Ctrl+Space: the main window's button must read "Resume" and
  its name, Alt+U must press it, and Playback > Play must read Resume too.
- [ ] Stop playback. Radio returns to Play. Cast returns its primary button to
  Play and makes separate Stop unavailable. Do not duplicate Play in that row.
- [ ] Repeat with no selection, a folder/view, live Radio, loading, natural
  completion, and failure. No enabled action may promise an impossible result.
- [ ] Invoke actions by keyboard. Labels, spoken names, menus, and hotkeys must
  agree; refreshing the state must not steal focus. Record exact speech/state.

Coverage: `tests/unit/core/test_transport_button.py` (every label and sentence
the shared module can produce), `tests/unit/ui/podcasts/test_cast_transport_row.py`
and `tests/unit/ui/radio/test_main_transport_button.py` (both rows on fake
hosts, every state), `tests/unit/ui/test_button_mnemonics.py` (the real Radio
frame against its real menu bar), and GATE-15 with run-time labels. This
cross-app physical reader and main-window enablement matrix remains unrun;
record exact speech after running it. Two conscious gaps to listen for: Radio's
status-bar Play cell and the player panel's Play/Stop button still say the
bare verb.

### Cast Find in Library

- [ ] In Cast's main window press Ctrl+F: focus is in "Find in library". Type
  part of a podcast name: nothing is spoken per letter; when you stop, the count
  is spoken once.
- [ ] Down Arrow: the first match is read with what it is ("-- a podcast",
  "-- an episode of ..."). Enter plays it; the Play button names it; Shift+F10
  opens the usual menu.
- [ ] Escape from the box: "Back to your library", and the cursor is on the row
  it was on before searching.
- [ ] View menu: Find in Library shows Ctrl+F; Customize Features shows
  Ctrl+Alt+C and opens with that key.

### Cast Episode Filter Tests

- [ ] Open a podcast's Episode Filters, Add Rule. Alt+S reaches "More tests";
  Alt+A opens "Episode Filter Test" with focus on "Look at". Choose Show
  notes, Test "contains", Value "sponsor", Save: the list reads "Show notes
  contains "sponsor"" and "Test added" is spoken.
- [ ] In Episode Filter Test choose Look at: Episode type. The Test list
  becomes whole phrases ("is a trailer") and Value is dimmed. Choose Length
  in minutes, type "ten" and Save: refused with the reason, focus on Value.
- [ ] Set Match when (Alt+W) to "Any one test is enough" with two tests, then
  Try It on Recent Episodes (Alt+Y): the count and up to five titles are
  spoken once; Alt+U reads the same sentence. The rules list row starts
  "Any one of:".
- [ ] On an episode you do not want, Shift+F10, F: Episode Filters opens and
  the rule window appears on its own; its first line says why the rule was
  chosen and how many of the newest it catches. Save the rule: "Rule added
  and filtering switched on". Cancel Episode Filters: nothing was stored.

### Cast Phase 1 Small Fixes

Each row is one small Phase 1 fix, checked by ear in QUILL Cast's main window
or the named dialog. Record exact speech.

- [ ] Press Ctrl+, in Cast. In the Podcasts group, "Where to land on launch"
  (Alt+U) reads "What is new..."; choose Favorites, OK, close and reopen Cast:
  focus lands on Favorites even when it is empty. Set it back to What is new.
- [ ] Open an episode's Show Notes, choose View as: Rich text, then Tab. The
  formatted notes are announced as "Show notes, formatted"; Alt+F reaches
  them; choosing Plain text hides the label with them.
- [ ] Press F1 in the main window (focus on the library) and in Feed Check.
  The first paragraph describes the window as it is now: the main window's
  buttons name their object, places are in the View menu, F6 reaches the
  status bar; Feed Check is worst first and opening it checks nothing.
- [ ] With the network off, Preview a search result in Add Podcast: the
  failure is spoken once, and Preview is usable again. Import an OPML file
  with feed checking on while offline: either per-feed results, or "The
  feed check could not run. Everything you imported is kept" -- never
  "checked 0 feeds".
- [ ] Shift+F10 on a podcast in the library: the menu says Unfollow...
  (Delete). Preview a search result in Add Podcast: the button says Follow.
  Podcasts menu: Follow ACB Media Podcasts. Unfollow a podcast, press
  Ctrl+Z: "Undid Unfollow" and what came back. No surface says Subscribe
  except where it names the OPML subscription-list file.
- [ ] Open Settings for This Podcast on a podcast with its own speed. Beside
  the speed field, the button reads "Use shared default for" and the
  setting's name; pressing it drops only that answer. Use Shared Defaults
  (Alt+D) asks first and says how many it dropped.
- [ ] In the main window's library tree, press Shift+F10 on a podcast, a
  folder, a pinned view and an episode, then the Applications key on each.
  Each opens the same menu a right-click does, once (not twice).
- [ ] Open Downloads, Podcasts > Feed Check..., an episode's Show Notes,
  Listening Statistics, and Year in Review from Statistics. Each opens with
  focus on its list, notes or report -- the first thing read after the
  title is content, not a filter or a button.
- [ ] Press Ctrl+Shift+Q (or View > Play Queue...): the Play Queue opens with
  focus in the queue list and its title read once. In QUILL, open the Sticky
  Notes Browser: it opens with focus in the search field.
- [ ] In Simple mode (View > Advanced Features unchecked), open Help: Keyboard
  Shortcuts... (Ctrl+Alt+Shift+W) and Global Hotkeys... (Ctrl+Alt+Shift+H)
  are present and open their windows; the Advanced Features announcement
  now counts two fewer rows.
- [ ] Smart Playlist Rules, Podcast Settings, Settings for This Podcast: the
  OK button is announced as "OK" with no shortcut; Alt+O does nothing; Enter
  saves and closes.

### Radio and Cast Closing Report

Entry: Quill Radio and QUILL Cast. To force a failure, make the data folder
read-only (or fill the disk) just before closing, then restore it.

- [ ] Close Cast with the folder read-only. It closes as usual. Restore the
  folder and start Cast: one sentence says it could not finish saving and
  names what; it is not repeated on the next launch.
- [ ] Help > Recent Problems: a "Closing" row is there; Retry says the
  library and statistics were saved now.
- [ ] Repeat in Radio: the sentence names noting when it closed or the
  recording note; Retry while recording keeps the recording note and says so.
- [ ] A normal close of either app says nothing at the next launch.

### Lite Background Open

Entry: a plain text file of several megabytes on a local disk, and any small
file on a network share.

- [ ] File > Open the large file. A new window's title says its number and
  "Opening"; "Opening" and the name is spoken once; typing does nothing until
  the text arrives; then focus is at the top of the text and the title is the
  file's.
- [ ] Open it again while it is still opening: focus moves to that window; no
  second window opens.
- [ ] Open the large file and press Ctrl+W at once: the window closes, nothing
  is announced later, and nothing appears in another window.
- [ ] Open the network file, then disconnect the share before it arrives (or
  use a path that cannot be read): the box names the reason and asks Try
  again?; No closes the empty window, Yes reads again.

### Lite Multi-Instance Settings

Entry: start QUILL Lite, then start a second with `--new-instance`.

- [ ] In the first, turn Word Wrap off (Alt+Z). In the second, change the
  theme in Preferences. Close the first, then the second. Start QUILL Lite:
  Word Wrap is off and the theme is the one the second chose.
- [ ] With both open, change a setting in one: the other does not change or
  announce anything until it is restarted.

### Lite Settings-Save Failure and Retry

Implemented in commit `6eaab53`. Accepted choices stay active for the current
session when writing settings fails. This is separate from document saving.

Entry points: Tools > Preferences (Control+Comma), plus ordinary settings
changes such as word wrap or appearance. Use a disposable development/test
profile and a controlled write failure; do not make the real user profile
read-only or fill the machine's disk to test this.

- [ ] Accept a setting while its store cannot be written. Expect:
  **Settings could not be saved. They remain active for this session. Reopen
  Preferences to retry.** Confirm Preferences does not then falsely say
  **Preferences saved**.
- [ ] Confirm the chosen setting works in the current session despite the
  persistence failure. The editor remains usable and the document is unchanged.
- [ ] Use F6 to review the status bar's Message cell. The failure remains
  reviewable after another action, document editing, and ordinary message expiry.
- [ ] Repeat a failed change. Check warning coalescing and configured speech
  throttling; record any missing failure outcome or excessive repeated warning.
- [ ] Restore write access and reopen Preferences. It retries already accepted
  settings without another edit or OK. On success, expect **Settings are now
  saved**, and the persistent warning clears.
- [ ] Make a new edit inside that reopened Preferences window and Cancel.
  Cancel discards that new edit; it does not undo the successful retry of choices
  accepted earlier. Reopen/relaunch to confirm only accepted values persist.
- [ ] With a settings warning queued, exit. It must be reported before teardown
  rather than delivered into a destroyed window. No exception dialog should appear.
- [ ] Repeat the failure with the status bar hidden. Record whether the spoken
  warning is sufficient and whether a review route is discoverable.

Coverage: 50 settings/status/Preferences/lifecycle tests, including real
filesystem failure followed by a successful atomic write, stale-warning
suppression after retry, preserved session values, and a pending warning at exit.

Limits: direct Retry/Open Settings Folder activity actions and adoption by other
settings/history writers remain open. Fault injection and diagnostics must not
expose raw filesystem errors, user paths, or sensitive contents.

### Lite Activation and Alt+Tab Focus

Implemented in commit `53406c3`. Activation makes one event-loop focus check
and one bounded settling check. Old checks are invalidated when activation
changes. Only container/missing focus is repaired; intentional control focus
must be left alone. The app does not announce the focus move itself.

Entry point: open a Lite document and switch to another application with Alt+Tab.

- [ ] Alt+Tab back repeatedly, then type immediately. Text must enter the
  active document, not disappear into the shell or MDI client. Confirm ordinary
  reader focus speech is not duplicated by an app announcement.
- [ ] Leave and return while a Find field or another interactive control has
  focus. That control must keep focus and remain usable; typing must not be
  redirected to the document unexpectedly.
- [ ] Repeat around open menus. Navigation must remain in the menu rather
  than being interrupted by the delayed focus repair.
- [ ] Rapidly leave again before the settling check. The app must not steal
  focus back from the newly active application.
- [ ] Repeat with several documents, after switching with Control+Tab or
  Control+F6, after opening a child, and after closing the active child. Focus
  must refer to the currently active document, never a destroyed or old child.
- [ ] Minimize/hide the shell and close it while activation work is queued.
  No background focus grab, stale speech, or exception dialog should occur.

Coverage: 21 focus tests, including real wx MDI/text controls over five
repair/preserve cycles; the preceding activation/lifecycle suite passed 28 tests.
Physical Alt+Tab and actual reader output remain human acceptance, not automated
passes. A reusable family helper and unsuccessful-repair diagnostics remain open.

### Lite Inbox and Exit Lifecycle

Implemented in commit `fb9f32d`. Confirmed Exit/shell close stops app-owned
polling before child destruction; final cleanup is idempotent. Cancelled close
keeps the app active. Pending external open requests are retained for a later
launch, and a deferred launch-update check does not start after shutdown.

Entry points: normal Exit, Alt+F4 on the shell, and opening a file through a
second Lite launch while the first instance is running.

- [ ] Exit with several documents. Save/discard prompts must remain operable,
  and exit must not cause a late document window or exception dialog to appear.
- [ ] Cancel a save/discard prompt during exit. The existing app must remain
  usable and accept a subsequent file-open request from a second launch.
- [ ] Send a request around confirmed exit. Confirm no document opens in the
  dying shell; retained requests must be handled on the next appropriate launch.
  The queued-tick timing itself is covered by automated tests.
- [ ] Exit soon after launch. No deferred launch-update dialog should appear
  after shutdown begins. Repeated/final cleanup must not produce duplicate cues.
- [ ] Check focus and speech around prompts, veto, and successful close. Only
  intended action outcomes and existing native focus/title speech should occur.

Coverage: 23 construction/lifecycle/update tests, including forced close,
veto, repeated finalization, pending requests, and delayed checks.

### Shared Background Callback Lifetime

Implemented in commit `84de01d`. Task-manager shutdown suppresses queued and
late success, failure, and progress delivery. Work/results may continue to
exist; UI delivery suppression is not the same as cancellation.

- [ ] When testing an adopted app task, close its owner while it is pending.
  No later speech, focus move, status update, or exception may target the closed
  surface. Record the specific task and app, not merely a generic pass.
- [ ] Reopen a replacement surface and start another task. It must receive
  its own result, never the old surface's callback.
- [ ] Confirm that cancellation feedback and completed results follow the
  feature's documented policy; suppressing stale UI callbacks must not silently
  erase work that the feature promises to retain.

Coverage: 12 focused task-manager tests for queued success/failure/progress,
repeated invalidation, replacement tokens, shutdown, and retained futures.

Limits: per-surface token adoption, persistent Activity/Problems history, direct
timers, and arbitrary CallAfter callbacks are not completed by this manager fix.
Add each actual adoption here as it lands before asking for feature-level SR testing.

### Core Registry Ownership

Completed QC2 F-07 in commit `1822e4c`. This is an internal thread contract,
not a new reader interaction. No dedicated speech script is required.

- [ ] During normal app regression, confirm keyboard commands, command palettes,
  and extension commands still work, without new error dialogs or unexpected speech.

Coverage: 77 registry/Quillin tests and strict mypy. Worker access is rejected
before state changes or handler dispatch. Readers do not need to provoke that
programming-error path manually.

## Completed Changes and Validation

Original document title: QC3: Completed Quality Changes.

### 2026-10-02: Activity, Repeat Last Result, and truthful settings saves (F-01, F-02, F-10)

- `quill/core/activity.py` (wx-free, strict): `ActionResult` (action, object
  name, outcome, summary, reason, next actions, importance, details,
  operation id, time) rendered to speech, a row and a details page from one
  record; `ActivityLog` (newest first, bounded to 200, thread-safe,
  listeners, operations in flight); `Progress` and `ProgressAnnouncer`
  (phase changes and 25-percent milestones only, owner token silences a
  stale run); `restore_index` (focus back by identity, else nearest row).
- `quill/ui/activity_window.py`: the shared window (summary, list, details,
  Retry / Undo / Open / Open Folder dimmed with their reason as help, Copy
  Details, Clear List, Close), `report_result`, `repeat_last_result`,
  `ActivityMixin` for the app shell. QUILL: `quill/ui/main_frame_activity.py`
  (Help rows beside Status Page, command ids, menu-id map). QUILL Lite:
  `quill/apps/lite_window_activity.py` (`cmd_activity`,
  `cmd_repeat_last_result`), rows in `core/lite/commands.py`, parity map.
  Radio and Cast: `ActivityMixin` on `AppShellFrame` and two Help rows in
  `support_menu.py`. Keys F9 and Shift+F9 in `DEFAULT_KEYMAP` and both
  `APP_KEYMAPS`; keyboard reference regenerated.
- `quill/core/persistence_outcome.py` and `quill/ui/persistence_reporting.py`
  (F-01): `guarded_write` around `core/settings.save_settings`,
  `core/lite/settings.save`, `podcasts/history.save_history`,
  `podcasts/subscriptions.save_library` and `radio/history_store`; the
  reporter is installed once per app (shell, QUILL's menu hook, Lite's
  settings mixin with `speak=False` because that mixin already speaks once).
- `quill/ui/surface_lifetime.py` (F-02): a success or failure delivered after
  its window closed is recorded as a review row naming the window.
- Tests: `tests/unit/core/test_activity_results.py` (11),
  `tests/unit/ui/test_activity_window.py` (2),
  `tests/unit/apps/test_lite_activity.py` (5); Lite command coverage,
  reachability, dialog and accessible-name inventories re-snapshotted.
- Docs: QUILL user guide Help section and PRD 5.59d; QUILL CHANGELOG; QUILL
  Lite user guide ("Activity and Repeat Last Result"), key table and
  CHANGELOG; Cast user guide and 2.0 release notes; Radio user guide, 3.1
  release notes and CHANGELOG.
- Also: `episode_filters.rule_matches` builds its condition tests with
  `functools.partial` (mypy could not infer the default-argument lambda; the
  scoped mypy run was red on main).

### 2026-10-01: Cast Episode Filters -- far more tests, any-one-of, Try It, and Filter Episodes Like This

- Jeff asked for "Rules for the episodes you did not want" to be beefed up:
  regular expressions, and rules that can do far more conditionally. Regular
  expressions already worked on the title; what was missing was everything
  else a feed varies on.
- New `quill/core/podcasts/filter_conditions.py`: `FilterCondition(field, op,
  value, case_sensitive)` over title, show notes, people, episode type,
  length, age in days, season and episode number; text ops contains / does
  not contain / starts / ends / is / is not / wildcard / regex / not regex,
  number ops at least / at most / is / is not. A missing fact never matches a
  number test; an empty type is a full episode; an unreadable test makes its
  rule match nothing; every matcher is total.
- `EpisodeFilterRule` gains `conditions` and `match_any` (every test, or any
  one). Storage: version 2 is read and written only when a rule uses either,
  so a filter made the old way stays byte-for-byte version 1 for older
  builds; an unknown field or op is kept as unusable, never dropped. The
  speech says "All of:" or "Any one of:" before the tests, and the save
  gate's duration check counts a length test.
- New "Episode Filter Test" window (`ui/podcasts/episode_filter_test_dialog.py`);
  the rule editor gains Match when, More tests with Add / Edit / Remove Test,
  and Try It on Recent Episodes (count and first five titles, shown and
  announced).
- New `quill/core/podcasts/filter_suggestions.py` behind **Filter Episodes
  Like This...** (episode menu and Quick Action, key F): trailer or bonus
  type, else a series name shared with siblings, else an unusual length,
  else the exact title -- each checked against the 50 newest, never one that
  takes every episode. Episode Filters opens with the rule editor on the
  draft, its reason as the first line; keeping it switches filtering on in
  the draft, saved only with Save.
- Tests: `tests/unit/core/podcasts/test_episode_filter_conditions.py` (33),
  `tests/unit/ui/test_cast_episode_filter_tests_ui.py` (6); the 71 existing
  filter tests pass (the unknown-version test now uses version 3). Cast help
  and accessible-name snapshots updated.
- Documented in the Cast user guide (Episode Filters: More tests, Try it,
  Filter Episodes Like This), the release notes (1.1.0 section and the rules
  section), PRD 21.5, the tutorial "Stop the parts of a podcast you did not
  want" (three new steps), Cast CHANGELOG 1.1.0 and the family CHANGELOG.
  Manual script "Cast Episode Filter Tests" added.

### 2026-10-01: Audio Description Project leftovers removed

- Jeff asked for the Audio Description Project to be gone from the
  Community menus. The menus, the `main_frame_adp` mixin and `quill/core/adp`
  were already removed in `fef27b3`; a sweep found what remained: the macOS
  test-build workflow still ran the deleted `tools/generate_adp_client_key.py`
  (a step that could only fail -- now "Generate the build-identity module"),
  and comments in `radio.py`, `radio_settings_menu.py` and `podcasts_menu.py`
  still described the ADP menu. All gone. Historical changelog entries are
  left as history.
- Audio description itself is unchanged and stays: Quill Radio's described
  tracks, Audio and Described Audio (Ctrl+Shift+A), Play Described Audio
  (Ctrl+Alt+D) and the once-per-video announcement. A first pass misread the
  request and removed those; it was fully restored before anything was
  committed, and the Radio audio-track, video, menu and video-command tests
  (98) pass against the restored code.
- Documented in the family CHANGELOG.

### 2026-10-01: Cast Phase 1 -- Find in library above the tree (interim of P10)

- New `quill/ui/podcasts/library_find.py`: `find_rows` (podcasts with unheard
  counts, episodes newest first, notes -- each row "<name> -- <what it is>",
  tagged with the library's own item data so Enter, Play and Shift+F10 work
  unchanged), `match_count_sentence`, and `CastLibraryFindMixin` (350 ms pause,
  count announced once and shown under the box, 200-row cap with a "more" row,
  Escape or emptying restores the library and the cursor, Down moves in,
  `focus_library_find`). The main panel builds "Fi&nd in library:" and the box
  above "&Library:" (label first, inline help, VoiceOver name); the panel's
  mixin inherits the Find mixin so `podcasts.py`'s class line is untouched.
  `_reload_library_tree` refreshes matches while Find is active; room made by
  moving `_toggle_resume_on_launch` into `podcasts_preferences.py` (budget
  ratcheted to 779). View > Fi&nd in Library is Ctrl+F.
- Found on the way: `podcasts_view_menu.py` was outside the app
  menu-accelerator gate since it was split out; added, and its first run found
  Customize Features with no key -- now Ctrl+Alt+C, Radio's chord for it.
  The accessible-name snapshot also picked up the two Preferences search
  controls from 1822e4c, which had been failing that test.
- Not done here: transcripts (F-09's index), and the plan's ranking of places.
- Tests: `tests/unit/ui/podcasts/test_cast_library_find.py` (10); help,
  name and accelerator gates; 2,199 Cast/label/menu tests pass.
- Documented in the Cast user guide (main window, View menu), release notes
  and PRD 23.13. Manual script "Cast Find in Library" added.

### 2026-10-01: F-02, adoption -- a window's background work stops at the window

- New `quill/ui/surface_lifetime.py`: `lifetime_for(window)` (one
  `UiLifetimeToken` per window, invalidated by its own `EVT_WINDOW_DESTROY`, not
  a child's); `SurfaceTasks` / `surface_tasks(manager, window_getter)` (submit
  adds the token and wraps every callback in a delivery-time check that the
  window is neither destroyed nor scheduled for destruction -- a top-level
  `Destroy()` only queues the window, and `EVT_WINDOW_DESTROY` comes at the
  next idle; `None` stays `None` so existing `is None` checks keep their
  meaning; everything else passes through).
- Adopted with one line per surface: Cast's Add Podcast (and Preview through
  it), OPML import, Podcast Manager; Radio's browse tree, station browser, link
  finder, ACB Media schedule; Weather's Center and Add Location; Publishing's
  browse dialog. GATE-11 kept by moving the Weather Center's five text helpers
  to `quill/ui/weather/center_text.py` and `ScheduledPublishChoice` to
  `quill/core/publishing_schedule.py`.
- Tests: `tests/unit/ui/test_surface_lifetime.py` (7): the token ends with a
  real wx window and not with a child; a queued top-level window already
  counts as going; a real `TaskManager` through the wrapper delivers while the
  window lives and drops a result after `Destroy()`; an explicit token is kept;
  pass-through; and the gate that no short-lived `quill/ui` surface stores the
  raw task manager (long-lived owners listed). 5,467 surface-related tests pass.
- Documented in the family changelog, Cast release notes and Radio 3.1.1 notes.
- F-02 stays open for reviewable terminal results (F-10's Activity store).

### 2026-10-01: F-12, in part -- timer ownership gate; the Player keeps its place on close

- New `tests/unit/ui/test_timer_ownership.py`: every `self.<x> = wx.Timer(...)`
  in `quill/apps` and `quill/ui` needs a stop somewhere -- `self.x.Stop()`, a
  `timer = getattr(self, "x")` then `timer.Stop()` (or `.Stop` handed on as a
  callable), or a loop over attribute names whose body stops them -- resolved
  per function. Shown its three shapes first. `ALLOWED` is empty.
- Its first run found Quill Player's `_resume_timer` and `_status_timer` (and
  an unstopped `_sleep_timer`) and Quill Converter's `_ipc_timer`. New
  `quill/apps/player_close.py` (Player at its GATE-11 budget) saves the resume
  position, stops all four Player timers and skips; previously the position was
  saved only every fifteen seconds and never on close. The Converter gained
  `_on_converter_close` stopping its IPC timer.
- Already in this session, and counted toward F-12: the `show_modal_dialog`
  label gate, Cast's initial-focus gate and the button-object gate.
- Validation: the gate (3 tests, one behavioural for the Player close); 353
  Player and Converter tests pass. Documented in the Player user guide, the
  Converter changelog (unreleased 1.0.0) and the family changelog.
- F-12 stays open for safe absence, performance and release invariants.

### 2026-10-01: X-07, first half -- Gemini model names from Gemini's own list work

- Reviewed PR #1615 (`feat/gemini-api-key-support`, open). Its central bug fix
  is real: Gemini's `GET /v1beta/models` returns `models/<id>`, and QUILL
  interpolated that into `/v1beta/models/{model}:generateContent`, producing
  `/v1beta/models/models/<id>`, a 404. Taken: a `gemini_model_id` normaliser
  used by `chat_endpoint`, `stream_chat_endpoint`, Gemini TTS and the model
  list. Not taken as a whole: the PR also rewrites unrelated error-extraction
  and endpoint-security code, edits a UIA workflow and Radio site copies, and
  adds silent provider inference ("gemini" in a model name) with a fallback to
  any stored key -- which would send a request to a provider the person did not
  choose, against X-07's consent requirement.
- `quill/core/ai/endpoints.py` (new, wx-free) holds the three URL builders,
  extracted from `assistant_ai.py` under GATE-11 and re-exported there;
  `assistant_ai.py`'s budget ratcheted to 1535.
- Tests: `tests/unit/core/ai/test_gemini_model_routes.py` (8): pure prefix
  handling and no doubled segment from any builder; then the shipped client
  against a Gemini-shaped `ThreadingHTTPServer` on 127.0.0.1 -- the list gives
  usable names, a prefixed name generates and streams to the right path, a
  wrong key is a safe error that never repeats either key, and a blank key on
  the real host is refused up front. Synthetic keys; no live requests. All
  1,029 AI core tests pass.
- Documented in QUILL's user guide (AI Hub) and the family changelog.
- Remaining in the X-07 row: QUILL Lite's own-key Gemini provider, built with an
  explicit provider choice, its key in the shared store, model ordering and
  pricing, cancellation, and reader acceptance scripts.

### 2026-10-01: F-06 -- Radio and Cast keep a record of what closing could not save

- New wx-free `quill/core/shutdown_report.py`: `ShutdownReport.step(step, class,
  action)` never raises and records failures (step id, class, exception class
  name only); `sentence()` names must-record failures in plain words;
  `persist(data_dir)` writes a pending file and a Recent Problems row (new
  `problem_log.KIND_SHUTDOWN`, labelled "Closing"), or removes a stale pending
  file after a clean close, and never raises; `take_pending` reads it once.
- New `quill/ui/shutdown_notice.py`: `surface_previous_shutdown` (says it once
  at launch) and `register_shutdown_retry` (per-app Retry for "Closing" rows).
- Cast: `_cast_shutdown` steps classed (stats and library must-record);
  `_cast_launch_notices` replaces the bare media-health CallAfter and adds the
  notice and Retry (flush both now). Radio: teardown moved to
  `quill/apps/radio_shutdown.py` (last-seen and recording marker must-record),
  `radio_launch_notice` queued in `radio_launch_tasks.schedule`; its Retry
  keeps the marker while recording. Attribute lookups happen inside the guard
  (a half-built frame closing must still close; the existing close tests
  caught the first version).
- Tests: `tests/unit/core/test_shutdown_report.py` (11); the Radio close tests
  and 5,034 Radio/Cast/problem/close tests pass; reachability gate clean.
- Documented in both user guides (Recent Problems), Radio 3.1.1 notes, Cast
  release notes and PRD 23.12, family changelog. Manual script "Radio and Cast
  Closing Report" added.

### 2026-10-01: F-05 -- QUILL Lite opens large and networked files off the UI thread

- New wx-free `quill/core/lite/open_prepare.py`: `prepare(path, mode)` (read
  and decode, or RTF safety-scan, into an immutable `PreparedDocument`) and
  `prepare_in_background(path)` (1 MiB or more, or a UNC path).
- `lite_window_file.py`: `load()` is now prepare + `_commit_load`, so its
  synchronous contract and every caller are unchanged; `_commit_rich` /
  `_commit_plain` replace the readers; `stop_timers` cancels a pending open.
- New `quill/apps/lite_window_open.py` (`DocumentBackgroundOpenMixin` on
  `DocumentFrame`): new window, read-only while empty, "Opening <name>" once on
  speech, status and title; the read on the app's lazily created two-worker
  `TaskManager` with a per-window `UiLifetimeToken`; commit only for the current
  generation, a live window and a running app; closing is Cancel; failure asks
  Try Again (No closes an empty window). `lite.py` routes large and networked
  opens there, counts a still-opening file as already open, and stops the pool
  in its shutdown owner (lite.py kept within its 627-line budget).
- Tests: `tests/unit/apps/test_lite_background_open.py` (16): prepare on real
  files (cp1252 and CRLF kept, RTF sanitised, unreadable raises, the policy);
  the window half on a stand-in with the shipped methods (busy, commit, stale
  generation, cancel, destroyed window, shutdown, Try Again, decline); one run
  through the real `TaskManager` and wx event loop asserting the commit ran on
  the main thread; app routing and the duplicate check. All 1,737 Lite tests,
  banned-pattern, dialog-contract, GATE-12, GATE-13 and GATE-11 pass.
- Not done: "Open as Plain Text" on failure, and a latency budget test for a
  large open; recorded here rather than claimed.
- Documented in the Lite user guide, PRD 5.3c, 1.2.0 notes and changelog, and
  the family changelog. Manual script "Lite Background Open" added.

### 2026-10-01: F-04 -- a focus repair that does not take is counted, privately

- `quill/apps/lite_shell.py`: after `control.SetFocus()`, the repair reads
  `FindFocus` again; if focus is not on the editor, `_note_repair_miss` bumps
  `focus_repair_misses` on the shell and logs `QUILL-LITE-FOCUS-MISS` with the
  holder's class name and the session count. No titles, labels or text; no
  announcement. A module function, so the shells the focus tests bind the
  shipped methods to need nothing new.
- Family helper: deliberately not extracted. QUILL's activation repair (#170)
  is a different mechanism on a different frame, and a helper with one caller
  is speculation; the rule (extract on the second adopter) is written into the
  function's docstring and the Lite PRD.
- Tests: three new in `tests/unit/apps/test_lite_alt_tab_focus.py` (counted
  and logged; a repair that takes is not counted; the log carries a class
  name, never window text); all 24 pass.
- Documented in Lite PRD 5.3b and the 1.2.0 changelog. The manual Alt+Tab
  scenarios in "Lite Activation and Alt+Tab Focus" still stand; F-04's manual
  acceptance remains there.

### 2026-10-01: F-11 -- two QUILL Lites stop undoing each other's preferences

- New wx-free `quill/core/lite/settings_merge.py`: `load_if_present` (None for
  a missing or corrupt file, so a merge never resets untouched fields to
  defaults) and `merge_for_save(baseline, ours, disk)` (per field: ours where
  this process changed it since the baseline, disk otherwise). Kept out of
  `settings.py`, which is at the 600-line cap.
- `lite.py` records `_settings_baseline` after loading; `save_settings` merges
  against the file when a baseline exists and refreshes the baseline after a
  successful write. Stubs without a baseline keep the old whole-object write.
  The in-memory settings are never replaced, by design (X-05).
- Tests: `tests/unit/core/lite/test_lite_settings_merge.py` (7: the merge,
  aliasing, unreadable files, and two real persistence objects against one
  real file, including "the running instance is not changed"); the existing
  settings-save failure tests; all 1,716 Lite tests pass.
- Documented in the Lite user guide (Opening a second QUILL Lite), PRD 5.3a,
  1.2.0 notes and changelog, and the family changelog. Manual script added
  ("Lite Multi-Instance Settings").

### 2026-10-01: Cast Phase 1 -- Preferences extracted, with "Where to land on launch"

- `quill/apps/podcasts_preferences.py` (`CastPreferencesMixin`) now owns
  `_open_preferences`; `podcasts.py` lost 137 lines and its GATE-11 budget was
  ratcheted down to 792. New row "Where to land on la&unch:" (Podcasts group)
  over `launch_place.CHOICES`, saved to `PodcastSettings.default_launch_view`
  with the library, and only when it changed. "Switch to Now Playing when
  playback starts" is deliberately not added yet -- there is no Now Playing to
  switch to -- and has moved into the Now Playing row.
- Tests: new `tests/unit/apps/test_cast_preferences_launch_place.py` (5, the
  real method against a fake dialog: the row, its default, saving, not
  re-saving, reopening selected); two source-reading tests repointed at the
  new module; 215 Preferences/help/settings-doc/budget tests pass.
- Documented in the Cast user guide (Preferences, Where Cast opens), release
  notes and PRD 23.11. Manual check added.

### 2026-10-01: Cast Phase 1 -- the Show Notes formatted view has a name (6b item 14)

- `show_notes_dialog.py`: a "Show notes, &formatted:" label is created
  immediately before the `HtmlWindow` (the old one was consumed by the plain
  view), hidden and shown with it, and the view gained inline F1 help. The
  Notes reader of 5c remains Now Playing's job.
- Tests: `tests/unit/ui/podcasts/test_show_notes_rich_label.py` (creation
  order by AST, the toggle, the access key). GATE-14, control-label, Cast
  help and accessible-name gates pass. Documented in Cast release notes.
  Manual check added.

### 2026-10-01: Cast Phase 1 -- tests for `library_tree.py`

- New `tests/unit/ui/podcasts/test_cast_library_tree.py` (9 tests, fake tree, real
  library objects, view membership stubbed since `virtual_views` has its own
  tests): an empty view gets no expander; a counted view gets one tagged
  placeholder; an episode view names the podcast on every row, newest first;
  205 pairs show 200 rows and "5 more"; Favorites opens to podcasts, each
  with its own episode expander and none for a podcast with no episodes;
  Play takes the newest unstarted episode, Continue Listening the most recent
  started one, Favorites a favourite's newest unplayed, and an empty view
  returns None so the caller can say why. GATE-15's roster entry landed in
  `fef27b3`. Documented in Cast PRD 23.3. No user-visible change.

### 2026-10-01: Cast Phase 1 -- F1 purposes for the main window and Feed Check

- `core/podcasts/surface_help.py`: the "QUILL Cast" purpose names what the
  reworked window has (buttons that name their object, View-menu places, F6
  to the status bar) instead of "open an episode list for more actions"; the
  "Feed Check" purpose says worst first, opening checks nothing, Retry and
  Retry All Failed, and that Cast never stops trying a failing feed. The two
  test updates in the same row landed in `fef27b3`.
- `docs/f1-help-reference.md` regenerated (GATE-HELPREF) and rendered.
  GATE-CAST-HELP and 28 help tests pass. Documented in Cast release notes.
  Manual F1 check added.

### 2026-10-01: Cast Phase 1 -- `labelled_field` takes no help

- `quill/ui/labelled_field.py`: the `help=` parameter and its internal
  `SetHelpText` are gone; the docstring says why (the audits read help at the
  construction site, so help set in a helper is `help-elsewhere`) and shows
  the caller setting it on the next line. It had no callers yet, so nothing
  else changed.
- Tests: new `tests/unit/ui/test_labelled_field.py` (no `help` parameter; the
  label is created and added before the control, on a real wx frame); control
  label gate tests pass. Documented in Cast PRD 23.9. No user-visible change,
  so no manual check.

### 2026-10-01: Cast Phase 1 -- two silent failures spoken (6b items 4, 20)

- `preview_command.py`: Preview's failure is announced as well as set on the
  status label (a label is silent to a screen reader).
- `opml_import_dialog.py`: the feed check's task failure no longer lands in
  `_on_validated([])`, which reported "checked 0 feeds, 0 unreachable"; the
  new `_on_validation_failed` sets and speaks "The feed check could not run.
  Everything you imported is kept; Podcasts, Feed Check shows which feeds are
  healthy." (no exception text -- it can carry an address), then shows the
  report.
- Tests: `tests/unit/ui/podcasts/test_spoken_failures.py` (both behaviours on
  fakes, and that the task's on_failure is wired to the new handler); 78
  related UI tests; GATE-13 clean.
- Documented in the Cast user guide (Importing a large subscription list) and
  release notes. Manual check added. The wider silent-label sweep (survey item
  12, 26 sites) stays in Phase 3.

### 2026-10-01: Cast Phase 1 -- Follow everywhere (6b items 9, 10)

- The six named labels, and every other user-visible "subscribe" a sweep of
  Cast's UI and core found: the library row menu (Un&follow..., f free in that
  menu), Preview's &Follow, "Follow ACB Media &Podcasts", Add Podcast's
  Preview/address-field names and failure line, extras ("&Follow This
  Podcast", "You already follow that podcast", "Now following ..."), Delete
  Folder's choice and its two sentences (using `following_count`, so no
  "podcast(s)" is read aloud), the folder-delete reassurance, the Manager's
  check-now refusals, Podcast Settings ("&When I unfollow"), the share-link
  refusal, the shared undo label ("Undid Unfollow") and its plain announcement
  (now `follow_words.unfollowed`), Statistics' "(no longer followed)", the
  refresh-policy and check-state sentences, the add-by-address outcome (shared
  with Radio), the Quick Actions row, and two Preferences labels. Radio's
  Browse "feeds cannot be checked" matches. Internal identifiers unchanged.
- Tutorials: three Cast lesson steps; Cast's tutorial book regenerated.
- Validation: 6,122 Cast, Radio, tutorial and doc tests pass (five tests
  updated to the new words). GATE-14 and the access-key rules hold.
- Documented in the Cast user guide (eleven passages), tutorials, release
  notes and PRD 23.1, and Radio's 3.1.1 notes and user guide (the undo
  sentence). Manual check added to "Cast Phase 1 Small Fixes".

### 2026-10-01: Cast Phase 1 -- "Use shared default", not "Follow" (6b item 19)

- `show_settings_panel.py`: the per-setting revert button is labelled "Use
  shared default for <setting>" through the shared `object_label` (elided at
  60), and its inert `SetName` is gone (on macOS it replaced the label with a
  sentence). `show_settings_dialog.py`: "Follow &the Shared Defaults" is "Use
  Shared &Defaults", and its confirmation title matches. The per-podcast
  tutorial step says the same; Cast's tutorial book regenerated (GATE-TUTDOC).
- Validation: GATE-14, Cast help audit, accessible-name audit, control-label
  gate and F1 reference all pass; 135 settings/tutorial tests pass.
- Documented in the Cast user guide, tutorials, release notes and PRD 23.10.
  Manual check added to "Cast Phase 1 Small Fixes".

### 2026-10-01: Cast Phase 1 -- Shift+F10 on the library tree (6b item 3)

- `main_panel.py` binds `EVT_CONTEXT_MENU` alongside `EVT_TREE_ITEM_MENU` to
  `_on_library_context_menu`, which already built its menu from the selection
  rather than the event -- so a keyboard request, which carries no item, gets
  the right-click menu. Radio's pattern from aaed65f.
- Gate: `tests/unit/ui/podcasts/test_library_tree_context_menu.py` (both
  events bound to the one handler, by AST; the handler builds the same menu
  with no event and with an empty one). 110 Cast UI tests pass.
- Documented in the Cast user guide (main window) and release notes. Manual
  check added: confirm a right-click does not now open the menu twice.

### 2026-10-01: Phase 1's "Commit" row retired

- The Cast Phase 1 Delivery Gate ("- [ ] Commit.") is removed at Jeff's
  request: every Phase 1 item now lands as its own commit pushed to main, so
  a separate end-of-phase commit row no longer describes anything. Its
  dashboard row went with it and the counts were recomputed.

### 2026-10-01: Cast Phase 1 -- windows open on the thing they are for (6b)

- Downloads and Feed Check focus their list, Show Notes its notes field,
  Listening Statistics and Year in Review their report, each in `show()`
  before `show_modal_dialog` (ShowModal keeps a focus already placed). The
  Play Queue half of the row landed in the previous commit, as a crash fix.
- Gate: `tests/unit/ui/podcasts/test_initial_focus.py` pins, by AST, that each
  of the six windows focuses its named control before the modal loop.
- Validation: the new gate plus all 107 Cast UI tests pass; GATE-11 and the
  dialog inventory pass. Documented in Cast release notes ("Smaller fixes")
  and the user guide (Feed Check). Manual check added to "Cast Phase 1 Small
  Fixes".

### 2026-10-01: Three windows that raised TypeError on open

- Found while giving Cast's Play Queue its title (Phase 1, focus row): the
  call was `show_modal_dialog(self.dialog)`, and `label` is a required
  argument, so the Play Queue had been raising `TypeError` on every open --
  View > Play Queue and Ctrl+Shift+Q in Cast, and QUILL's podcast host. A
  whole-tree AST scan found two more: QUILL's Sticky Notes Browser (same
  crash) and the Global Hotkeys dialog's fallback branch (latent: every
  caller injects `show_modal_fn`). All three now pass title and announce.
- Gate: `tests/unit/ui/test_show_modal_dialog_calls.py` (detector shown a bad
  sample first; then the live tree). This is F-12's kind of gate -- a
  delivery promise ("this window opens") checked without building a window --
  recorded here rather than closing F-12, which is broader.
- Validation: the new gate plus 48 targeted UI tests pass. Documented in Cast
  release notes ("Smaller fixes") and the family changelog. Manual check
  added to "Cast Phase 1 Small Fixes".

### 2026-10-01: Cast Phase 1 -- the keyboard editors are everyday rows (section 8)

- `menu_mode.ADVANCED_ROWS` loses `keymap_editor` and `global_hotkeys` (with a
  comment saying why they left); `podcasts_menu.py` appends Help > Keyboard
  Shortcuts... and Help > Global Hotkeys... unconditionally. Simple mode now
  hides 16 entries (15 rows and the Quillins menu), not 18, and the switch
  announcement counts that.
- Validation: new `test_the_keyboard_editors_are_everyday_rows` plus the
  existing menu-mode tests (every declared row is gated, every reason ends in
  a full stop); menu accelerator gate. Documented in the Cast user guide
  (Simple and Advanced), release notes ("Smaller fixes") and PRD 23.4. Manual
  check added to "Cast Phase 1 Small Fixes".

### 2026-10-01: Cast Phase 1 -- OK buttons carry no access key (6b item 18)

- Smart Playlist Rules, Podcast Settings and Settings for This Podcast each
  had "&OK", spending Alt+O on a button Enter already presses (CLAUDE.md,
  GATE-14's first fix). Now plain "OK"; O is free in all three windows.
- Validation: GATE-14 and the dialog button-contract audit pass; 22 targeted
  UI tests pass. Documented in Cast release notes 2.0 ("Smaller fixes").
- Manual check: open each window, press Alt+O, nothing happens; Enter still
  saves. Added to the handoff below under "Cast Phase 1 Small Fixes".
- Counting: the dashboard's manual-scenario figure is now computed from the
  handoff section's unchecked boxes on every update (45, not the hand-kept
  36 -- the X-06 transport rows and this one had not been added to it), and
  every code count is recomputed from the trackers the same way.

### 2026-10-01: X-06 -- the transport button says its object (Radio and Cast)

Resolves X-06 and Cast Phase 1 item 1 together, because they were one defect
seen from two sides: a button that says only its verb, and a button that says
a verb that cannot happen.

- New wx-free `quill/core/transport_button.py`: one `face()` returns the
  button's label (verb, access key, object, elided at 40 visible characters,
  ampersands doubled), its full sentence, and its verb, from one reading of one
  state. Parameters: `active_verb` ("pause" for Cast, "stop" for Radio's main
  window), per-app `Mnemonics`, and the app's own dead-state hint.
  `label_samples()` hands GATE-15 every label the button can show.
- Cast: `core/podcasts/transport_intent.py` is now a thin reading of the
  shared module (`button_face`, `button_label`, `transport_name`,
  `label_samples`). `main_panel.py` builds every row button without
  `set_accessible_name`, with proportion 1 so the row never reflows;
  `podcasts.py` sets the label from the face; `places.py` grew
  `_transport_button_face` and `_unfollow_target` (the selected show, or the
  selected episode's show), and Unfollow's label names it. Stop is enabled only
  while playing or paused (unchanged).
- Radio: `quill/ui/radio/stop_button.py` is replaced by
  `quill/ui/radio/main_transport_button.py`: Play <favorite> (Alt+L), Stop
  <playing> (Alt+T), Resume <it> (Alt+U), "Play -- nothing selected" which
  announces the way out when pressed. Follows the favorites tree's selection.
  `_on_play_stop_button` (Ctrl+P, Playback > Play) presses it; the Playback
  row now reads the button's word (it read "Stop" while paused on a row that
  resumed). The Volume label moved from Alt+U to Alt+O: the bar owns every
  other letter of "Resume".
- Gates: GATE-15 gained `DYNAMIC_LABELS` (labels built at run time, checked
  like literals, reported with the providing module's path) and the Radio
  roster gained the new module. New
  `tests/unit/ui/podcasts/test_button_object_in_label.py` fails the build if
  `set_accessible_name` targets a `wx.Button` anywhere in Cast (shown a known
  bad sample first).
- Validation: 16 core transport-button tests, 11 transport-intent tests, 13
  Cast row tests on a fake host (`test_cast_transport_row.py`), 12 Radio
  button tests on a fake host and fake wx (`test_main_transport_button.py`),
  the GATE-15 tests including the run-time-label case, the real-frame Radio
  mnemonic test, and the Cast and Radio unit directories: 2,788 passed. GATE-15
  CLI clean. Platform report: see the commit.
- Documented: Radio user guide (main window, Playback menu), Radio release
  notes 3.1 (Unreleased), Cast user guide (main window), Cast release notes
  2.0, Cast PRD 23.10, family changelog. Manual reader script: the "Radio and
  Cast Transport State" handoff section, updated below.
- Not done here, and recorded: the ~40 `SetName` calls on buttons in Cast's
  dialogs (Add Podcast, Manager, Downloads, Statistics, Show Notes and others)
  are the same inert route by another name; they are Phase 5's wordlist and
  help sweep. Radio's status-bar Play cell and the player panel's Play/Stop
  face still say the bare verb -- a cell is a readout in a bar, and the panel
  has no selection to name -- which the handoff script records as a conscious
  choice to listen for.

### 2026-10-01: Second pass -- Lite exit crash, Cast documentation catch-up

- Fixed a QUILL Lite exit crash reported the same day (`RuntimeError: wrapped
  C/C++ object of type Panel has been deleted` from `_refresh_status`). The
  close path stopped the status bar's coalescing timer and then destroyed the
  window; teardown events called `_touch_status` in between and re-armed it.
  The stop is now one-way and a refresh that reaches a destroyed panel returns.
  Committed as `d8b4d1e` and pushed. This is an instance of F-02 (lifetime
  guards in short-lived surfaces); F-02 stays open for the general adoption.
- Validation: `tests/unit/apps/test_lite_status_lifetime.py` (3 new tests) and
  the three existing Lite status-bar test modules, 36 passed; ruff, GATE-11
  (after trimming comments to stay under the 620-line budget), and every
  pre-commit gate passed. Documented in Lite's release notes 1.1 (Unreleased
  Quality Fixes), Lite's changelog (Unreleased) and the family changelog.
- Re-verified the Cast Phase 1 claims against the source. Result recorded
  inline in section 15: the nine `[x]` rows are committed in `fef27b3`; none
  of the fifteen pending rows had landed, except that GATE-15 is on the
  `platform_report` roster and the two named tests were updated. Three Phase 0
  cores (`refresh_audio`, `inbox_removal`, `quick_plays`) have no window or
  key yet; the quick plays are reachable from the Command Palette only.
- Caught the Cast documentation up to everything Phase 0 and `fef27b3`
  shipped, none of which had reached the user guide, PRD or release notes:
  Follow vocabulary, Add Podcast (Preview, labelled fields, Following column,
  context menu), the pinned views opening, Play on an episode or a view, the
  View menu and its places, Simple/Advanced and Customize Features, the
  Podcasts menu rename and GATE-15, the Window menu, Unfollow and Episode List
  buttons, the status bar, Feed Check, launch landing, the three quick plays,
  GATE-CTLLABEL. Release notes 2.0 gained a dated section at the top; the user
  guide's Getting Started, main window, Menus (Simple and Advanced, Podcasts,
  View, Window), a status bar section and a Feed Check section were rewritten
  or added; the PRD gained section 23 with nine subsections. HTML and EPUB
  regenerated for the three changed documents.

### 2026-10-01: Document Consolidation

Two subsequent user requests add X-06 (Radio/Cast transport behavior) and X-07
(QUILL/Lite Gemini support review). These are pending work, not implemented
changes or passed manual checks. The current dashboard therefore counts 42
code/delivery groups and 36 manual scenarios. The 40-row count below records
the consolidation baseline, not the current total.

The Cast plan, family review, testing handoff, and completion history now live
in this single document. Original pending code claims and human test outcomes
were not newly verified or marked complete. Every remaining family finding has
its own stable-ID bottom tracker row. Category counts and VS Code todos mirror
the same grouped scope: 40 code/delivery rows and 35 manual test scenarios.

Maintain the dashboard and trackers after each verified implementation. Add UX
test instructions and evidence here before trimming finished code rows. When
work is paused, identify it as paused rather than leaving a false active status.

### 2026-09-30

- Beacon's existing context-help onboarding was extracted into the shared
  Preferences search module to preserve the dialog module's 3166-line budget.
  The budget was not raised. The 12 focused search/Beacon tests passed again.
  Radio's pre-existing mixed-ownership user-guide changes and regenerated
  copies remain outside the isolated search/registry commit.
- Full-worktree banned-pattern gate passed after native search integration.
  Final scoped Ruff checks passed. The first dialog inventory/hardening run
  timed out during repository source scanning, without a mismatch result.
  The rerun with a 300-second per-test limit passed all 7 registry/hardening
  tests; the source scan took 37 seconds, exceeding the default timeout.
  Only the existing unrelated invalid-escape warning was reported.
- Completed QC2 F-07: CommandRegistry checks its creating-thread ownership at
  every public state/dispatch boundary. Worker calls fail before side effects;
  immutable snapshots can travel to workers. The core remains wx-free.
- Validation: 77 registry and Quillin unit/integration tests passed; strict mypy
  on `quill/core/commands.py` reported success. Removed F-07 from remaining work.
- Implemented shared native Preferences/Settings search using existing dialog
  controls and the modal/modeless show contracts; Beacon's local setup installs
  the same helper. Labels, accessible names, and help are indexed, not values.
  Enter navigates without saving; Ctrl+F returns to search; Escape clears first;
  hidden book/Beacon pages are revealed; disabled controls remain disabled.
- Validation: 67 broader Preferences/dialog/Beacon tests passed, followed by
  29 search/dialog tests after modeless onboarding. Live tests cover Lite's real
  constructed dialog, companion controls, and Beacon's hidden Sync panel.
- Full all-app search is NOT complete: Converter, Player, and Inkwell lack a
  unified Preferences entry point; web forms and unopened nested dialogs are not
  indexed. Those gaps and manual screen-reader acceptance remain in QC2 and
  `docs/preferences-search.md`. No release or all-app completion claim is made.
- Focus repair committed as `53406c3`. Settings and focus manual screen-reader
  listening remain outstanding. QC2 now has 10 major findings, several partial.
- Added bounded Lite activation settling (QC2 F-04 implementation): two checks
  at most, invalidated by later activation/deactivation, with menu, visibility,
  shutdown, and intentional-control guards. Focus changes are not announced.
- Validation: 21 focus tests passed, including an actual wx MDI shell, child,
  editor, and Find-like field exercised over five repair/preserve cycles. The
  preceding combined activation/lifecycle run passed 28 tests. Physical Alt+Tab
  and screen-reader listening were not performed and remain tracked acceptance.
- Settings recovery committed as `6eaab53`; inbox shutdown as `fb9f32d`;
  shared callback lifetime as `84de01d`. No changes pushed or released.
- Fixed the silent Lite settings-write failure (QC2 F-01 implementation).
  Failures retain session values, expose a dirty-state warning in the status
  message, and report a safe diagnostic without exception text or user paths.
  Preferences no longer falsely claims success; reopening it retries already
  accepted settings. Pending warnings coalesce and flush before shutdown.
- Validation: 50 settings, status, Preferences, and lifecycle tests passed,
  including a real failed filesystem write followed by a successful atomic
  save, stale warning suppression after retry, and close with a pending warning.
- Updated Lite's PRD, user guide, unreleased release notes, announcement, and
  the family changelog. Their HTML/EPUB copies are regenerated with each commit.
- F-01 remains only for direct Activity/Problems actions, other persistence
  writers, and manual screen-reader acceptance; no claim that these are built.
- Added shared task callback lifetime guards. Shutdown suppresses success,
  failure, and progress delivery, including callbacks queued before shutdown
  and work finishing afterward. Optional per-surface tokens are one-way and
  independent of cancellation; replacement surfaces use new tokens.
- Preserved worker results in task futures without blocking `wait=False`
  shutdown. No persistent Activity/Problems surface is claimed.
- Added regressions for queued success/failure/progress, repeated invalidation,
  replacement tokens, running work after shutdown, and retained results.
- Validation: 12 focused task-manager tests passed.
- Completed QC2 F-03: Lite has one idempotent application timer shutdown owner,
  called by confirmed Exit, shell close, and final `OnExit`. Queued inbox ticks
  do not consume pending requests after shutdown. Requests remaining after a
  reentrant close are reposted; cancelled close keeps the app active. Deferred
  launch-update checks do not start after shutdown.
- Validation: 23 Lite construction, lifecycle, and update tests passed, including
  forced close, veto, repeated finalization, pending requests, and delayed checks.
- Updated Lite's PRD, user guide, unreleased release notes, and announcement.
- The first commit's isolated banned-pattern hook saw unrelated Cast dialogs
  without their existing staged inventory. The same gate passed in the full
  working tree; only that hook was skipped for the isolated commit. Formatting,
  lint, module budget, and generated-doc parity hooks passed.
- Updated the main PRD and changelog; trimmed the completed portion of QC2
  F-02 while retaining per-surface adoption and activity-history work.
- Existing staged and unstaged work is outside these commits unless explicitly
  recorded here. No changes have been pushed or released.

## Remaining Code Work

This is the authoritative unchecked code/delivery tracker: **20 grouped rows**. Manual tests live in Screen-Reader Testing Handoff. Preserve the detailed specifications above when trimming obsolete pending text. Record finished code and test evidence in Completed Changes and Validation, and add/update a UX testing script before removing its row. Recompute the dashboard and VS Code category counts after each removal.

### Family Reliability Findings: 4

- [ ] F-08: Extract ownership-heavy QUILL/Radio/Cast orchestration by lifetime/invariant; preserve host contracts and ratcheted size budgets.
- [ ] F-09: Implement bounded incremental Cast library/transcript search, feed refresh, and download state with performance/cancellation tests.
- [ ] F-10: Implement/adopt shared operation/result/activity/progress, focus-memory, repeat-announcement, and details contracts across apps. (Done 2026-10-02: `quill/core/activity.py` -- `ActionResult`, `ActivityLog`, `Progress`/`ProgressAnnouncer`, `restore_index`; the shared Activity window with Retry/Undo/Open/Open Folder/Details; F9 Repeat Last Result and Shift+F9 Activity in QUILL, QUILL Lite, Radio and Cast; persistence outcomes and outlived results reported through it. Remaining: adopt `Progress`/`ProgressAnnouncer` in Cast downloads and feed refresh and in Lite's background open; adopt `restore_index` in Cast's lists; route Cast's and Radio's existing operation outcomes (follow, refresh, export, record) through `report_result`.)
- [ ] F-12: Gate critical delivery promises, timer ownership, safe absence, performance, and release invariants with automated tests. (Done 2026-10-01: timer ownership, and three delivery-promise gates -- every `show_modal_dialog` call carries its label, six Cast windows focus their purpose, no Cast button is named through the inert route. Remaining: safe absence, performance and release invariants.)

### Family Product Requirements: 6

- [ ] X-01: Finish family settings search, including Converter/Player/Inkwell entry points, web forms, and unopened settings areas.
- [ ] X-02: Implement discoverable keyboard-accessible task recipes using existing commands and shared operation results.
- [ ] X-03: Implement reversible focus/review/session profiles using existing settings and truthful persistence.
- [ ] X-04: Finish richer queue/activity views and skippable first-run/task guidance without duplicating shared models.
- [ ] X-05: Implement specified explicit-opt-in cross-app personalization without silent keyboard/focus/screen-reader changes.
- [ ] X-07 (first half done 2026-10-01: Gemini `models/` prefix normalisation
  in every URL builder and the model list, with real-boundary tests; remaining:
  QUILL Lite own-key Gemini provider with an explicit, consented provider
  choice -- the PR's silent provider inference and fallback are not taken).
  Review and integrate the applicable changes proposed in
  [Gemini API-key support and endpoint routing, PR #1615](https://github.com/Community-Access/quill/pull/1615)
  for both QUILL and QUILL Lite. Add real-boundary unit/integration tests for
  models/ prefix normalization (no doubled models/models URLs), generateContent
  and streaming routes, Gemini/OpenAI provider and key selection, missing/invalid
  keys, model ordering, cancellation, and safe errors. Preserve explicit consent,
  secure key storage, and shared-editor parity. The PR's claimed live passes
  are not local verification. Use synthetic credentials in reproducible offline
  tests; when authenticated validation is needed, load the user-authorized
  S:\keys.txt only inside a local opt-in test process, never into chat, fixtures,
  logs, snapshots, or Git. Keep live API checks separate from offline unit tests;
  ask before sending content or incurring requests. Document the tested shared
  writing features and resulting reader acceptance scripts before closing this item.

### Cast Phase 1 Code and Tests: 1

Re-verified against the source 2026-10-01: fifteen were open; the first (the
button row's object in the label) closed with X-06, leaving fourteen. Partial
credit on two rows is noted inline. Worked top to bottom, one commit each.

- [ ] Now Playing (section 5), with the Notes reader and the grown Links
      dialog (5c) as its show-notes pane -- the reader is built once here and
      the Show Notes peer window in Phase 4 reuses it. Includes the Preferences
      row "Switch to Now Playing when playback starts"
      (`PodcastHistory.switch_to_now_playing`), moved here from the Preferences
      row on 2026-10-01 because a switch for a surface that does not exist lies.

### Cast Phases 2-7: 6

- [ ] Phase 2: Complete the one-window Places/content/Find host, Manager removal, customization, Notifications, feature switches, and gates.
- [ ] Phase 3: Complete meaningful shared status, Recent Problems, silent-outcome cleanup, and the regression gate.
- [ ] Phase 4: Complete shared peer surfaces and Watched Folders, settled-file background watching, Groups, settings, and notifications.
- [ ] Phase 5: Complete vocabulary/settings consolidation and refresh schedules, monitoring, migrations, Feed Check/menu wiring, and tests.
- [ ] Phase 6: Complete First Run, Tutorials, five documents, and the F1/help audit.
- [ ] Phase 7: Complete the twelve extensions specified in section 18, including keys, behavior tests, help, and shared implementations.

### Cast Follow-On Integrations: 3

- [ ] ChatGPT: Integrate the shared consent-gated adapter, settings, cancellation, and error handling.
- [ ] Text-only AI: Complete the specified independently switchable features using shared privacy/operation contracts.
- [ ] Earshot parity: Complete referenced R8-R10 and B1-B3 groups, with switches, documentation, and reachability tests.
