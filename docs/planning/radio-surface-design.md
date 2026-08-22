# Quill Radio: what belongs on the surface, and what belongs one key away

**Built and shipped.** Every question raised during review was answered; the
decisions are listed below and the reasoning for each sits in its own section.
Two of them were overturned during implementation by the repo's own gates, and
both overturnings are recorded in place rather than quietly edited away.

Date: 2026-08-21

## The problem

Two complaints, one cause.

The main window shows the favorites list **and** a row of player buttons: Play/Stop, Add to Favorites, Record, Chapters (when relevant), Browse Stations, and a Volume slider. Somebody arrowing out of the favorites tree passes six or more controls, most of which act on something that is not the tree.

The Playback menu holds **39 items** covering three unrelated questions: what the transport is doing, how the audio sounds, and what to do with video. (I first estimated twenty. The video and chapter items are appended flat into the same menu rather than sitting in a submenu, which is both the reason for the miscount and the reason the menu is unusable.)

Underneath both is an inconsistency the app already argues against itself about. `quill/ui/radio/player_panel.py` states the position plainly:

> A permanent player window buys one obvious place and costs a third citizen in the Alt+Tab rotation -- which is the thing that was being complained about in the first place. And with the transport keyboard now working in every window, an always-open player is mostly furniture.

The player was then given no window of its own -- it is summoned with Ctrl+Shift+G and returns focus to the exact control you left. But the main window is still a permanent player. The design decision was made and the landing page was never brought in line with it.

There is also a plain gap: the Browse window has a Mute toggle and the main window does not.

## Decisions

| Question | Decision |
| --- | --- |
| What is the main window? | A favorites list you play from -- not a player |
| Which controls stay? | Now playing (read-only), the tree, Mute, Volume |
| Where does "save the playing station" go? | Station menu on Ctrl+Shift+F **and** the player window |
| How does the Playback menu split? | 39 items become Playback (17) / Audio (11) / Video (8), plus Listening Statistics to View |
| Does Video appear and disappear? | No -- always present, greyed out when there is no video |
| Is there a "Controls" menu? | No -- Play, Rewind and Forward *are* playback |
| Do any keys change? | No |
| Is the now-playing line readable? | Yes -- read-only TextCtrl, focusable, copyable |
| What does it show? | Station and state, the track, one line of anything else true |
| Does it show elapsed time? | No -- Ctrl+Shift+W answers that on demand |
| Startup window setting? | One checkbox: "Open Browse Stations at startup", off by default |
| Where do What's Playing? / Song History go? | They stay in Playback |
| Quick navigation? | **Ctrl+G** opens a Go To popup: a numbered list of places, user-ordered |
| What happens to Recordings' Ctrl+G? | Recordings is a *place*: reached through Go To. Ctrl+R stays Record Now. |
| Is the Go To list configurable? | Yes -- order and membership, on the Choose Columns machinery |
| How many positions? | Ten: 1-9 then 0, all ten filled by default. A destination added later lands in the pool, never in the menu, so nothing renumbers |

## What changes

### 1. The main window becomes a list you play from

After:

```
Now playing:  +-----------------------------------+
              | Jazz24 -- playing                 |   read-only,
              | Take Five -- Dave Brubeck         |   focusable,
              | Recording                         |   copyable
              +-----------------------------------+
Favorite stations:  [tree]         <- focus lands here
-------------------------------------------------
[ Mute ]   Volume: [==========]
```

Five stops, down from eight or nine, and the same shape as the Browse window.

These controls come off the main window:

| Control | Where it lives instead |
| --- | --- |
| Play/Stop | Enter on a tree row, Ctrl+P, Playback menu |
| Add to Favorites | Station menu (new key) and the player window -- see section 2 |
| Record | Ctrl+R, the Record menu, the player window |
| Chapters | The player window, which already has them |
| Browse Stations | Ctrl+B, the Station menu, and the first-run flow |

Nothing loses its only route. Browse is worth calling out specifically: a brand-new listener never depended on that button, because `first_run_dialog.py` offers **Browse Stations Now...** on two of its three screens.

Mute is a `wx.ToggleButton` labelled `&Mute`, matching `browse_tree_dialog.py` exactly, and keeps Ctrl+M. It is the one control being *added* to the main window.

The now-playing line stays, and **changes from a `wx.StaticText` to a read-only
`wx.TextCtrl`**.

This is the one place the trimming adds a tab stop rather than removing one, and
it is worth it. A `StaticText` cannot take focus, so it cannot be arrowed
through, cannot be reviewed word by word, and cannot be copied. A track title,
a station name and a format are exactly the kind of text somebody wants to go
back over slowly -- and today the only ways to do that are F6 into the status
bar or Ctrl+T for the full Now Playing window. Both are fine, and neither
should be required to read the line already sitting at the top of the window.

Specifics that matter:

- `wx.TE_READONLY | wx.TE_MULTILINE`, so a long "station -- track -- artist"
  wraps and can be read a line at a time instead of scrolling sideways.
- **No `wx.TE_PROCESS_TAB`**, so Tab moves focus onward and the control never
  becomes a trap.
- Copy works for free, which quietly answers "what *was* that track?".
- Accessible name stays "Now playing".
- **Only write to it when the text actually changes**, and **never while it has
  focus**. A read-only field re-set on a timer re-announces itself under a
  screen reader, and rewriting it while somebody is reading it moves the text
  out from under them mid-sentence. Two guards: an equality check before
  `SetValue`, and a pending-update slot that is applied when focus leaves. This
  is the one real risk in the change, and it is entirely avoidable.

**What it says.** Today the line is one state sentence ("Radio: stopped",
"Playing Jazz24"). Now that it can be read properly it should carry what you
would otherwise press Ctrl+T for:

1. **Station and what it is doing** -- the existing status text, which already
   folds in muted and "(recording)".
2. **The track**, when there is one -- title and artist, from
   `_radio_now_playing_text()`, the same source the status bar and the
   announcements use.
3. **Anything currently true and worth knowing** -- recording, sleep timer
   running -- one short line, omitted entirely when there is nothing to say.

Lines are omitted rather than filled with placeholders. A station with no track
metadata shows two lines, not a line reading "no track information".

**What stays behind Ctrl+T.** Stream URL, format, bitrate, country, source, and
the track's provenance. That window is the "everything known" reference and
should stay reference; this field is the headline. The rule for deciding is
whether you would want it read to you *every time the station changes* -- the
station and the track, yes; the stream URL, no.

The ordering matters for the same reason: the slowest-changing fact is first,
so the start of the field is stable while a track name changes underneath it.

**Elapsed time and DVR position are deliberately excluded** (decided
2026-08-21). They are the one genuinely useful fact that changes every second,
and a field that rewrites every second either re-announces constantly or has to
be exempted from the change check that makes the rest of this safe. **Ctrl+Shift+W
("Where am I?") answers it on demand**, which is the right shape for a fact you
want occasionally and never want read at you.

The status bar keeps its own focusable "Now playing" cell (F6, Enter for full
details). That is not duplication worth removing: the status bar is a
scan-across-everything surface, and this is the headline.

### 2. Saving the station that is playing

This is the only capability that would otherwise be lost. `_on_favorite_toggle` in `quill/apps/radio.py` is currently reachable **only** from the button -- there is no menu item and no key. It also cannot simply move into the favorites tree's context menu, because the station it acts on is very often one you found in Browse and that is not in the tree at all.

Two homes, one handler:

- **Station menu**: "Add Playing Station to Favorites" on **Ctrl+Shift+F**. The label flips to "Remove Playing Station from Favorites" when the playing station is already saved, exactly as the button's label did. Disabled, and saying why, when nothing is playing.
- **Player window** (Ctrl+Shift+G): the same action as a button, alongside the transport it already carries.

Ctrl+Shift+F is unclaimed in Radio today, and sits beside Ctrl+Shift+M (Manage Favorites), which makes the pair easy to remember.

### 3. The Playback menu splits three ways

**First, a correction to the premise.** I said "about twenty items". It is
**39**. The video, chapter, transcript and speed items are not a submenu -- I
assumed they were, and they are not. `radio_video_menu.py` appends them
*directly into the Playback menu*, flat, alongside everything else. That is the
actual reason the menu is unmanageable, and it means "promote the video
submenu" was never the change; the change is a real three-way split.

Here are the three menus, item for item. Every key below already exists. None of
them changes.

#### &Playback -- what the transport is doing (17)

```
  Radio: stopped                          (readout, disabled)
  ----------------------------------------------------------
  &Play                                   Ctrl+P
  Re&wind 30 Seconds                      Ctrl+Shift+Left
  &Forward 30 Seconds                     Ctrl+Shift+Right
  Back to &Live                           Ctrl+Shift+L
  ----------------------------------------------------------
  Play &Faster                            Ctrl+Shift+Up
  Play Slo&wer                            Ctrl+Shift+Down
  &Normal Speed                           Ctrl+Shift+0
  ----------------------------------------------------------
  C&hapters...                            Ctrl+Shift+C
  Ne&xt Chapter                           Ctrl+Shift+.
  Pre&vious Chapter                       Ctrl+Shift+,
  &Transcript...                          Ctrl+Shift+T
  ----------------------------------------------------------
  &Go to Player                           Ctrl+Shift+G
  &Continue Listening...                  Ctrl+Alt+Shift+L
  What's Pla&ying?                        Ctrl+T
  Son&g History...                        Ctrl+Shift+H
  ----------------------------------------------------------
  Sleep &Timer...                         Ctrl+Shift+Z
  Wake-U&p Timer...                       Ctrl+Alt+Z
```

**Chapters and Transcript live here, not under Video.** A recording and a
podcast episode have chapters too. Filing them under Video would hide them from
everything that is not a video, which is most of what this app plays.

#### &Audio -- how it sounds (11)

```
  &Mute/Unmute                            Ctrl+M
  Volume &Up                              Ctrl+Up
  Volume &Down                            Ctrl+Down
  Volume &Boost                           Ctrl+Shift+B
  ----------------------------------------------------------
  &Output Device...                       Ctrl+Shift+D
  Sound &Enhancements...                  Ctrl+E
  ----------------------------------------------------------
  Use One &Volume for All Stations        (check)
  Forget Every Station's Own Volu&me...   Ctrl+Alt+Shift+V
  Announce Trac&k Titles                  (check)
  ----------------------------------------------------------
  &Audio and Described Audio...           Ctrl+Shift+A
  Play &Described Audio                   Ctrl+Alt+D
```

**Described audio is an Audio item, not a Video one.** Choosing an audio track
is choosing what you hear, and for a blind listener described audio is the
*main* track rather than an accessibility extra bolted onto video.

#### Vi&deo -- the picture (8)

```
  Show &Video                             Ctrl+Shift+V
  F&ull Screen                            F11
  Video Si&ze                             (submenu)
  ----------------------------------------------------------
  &Captions                               Ctrl+Shift+K
  Caption Se&ttings...                    Ctrl+Shift+Alt+T
  ----------------------------------------------------------
  Video &Information                      Ctrl+Shift+I
  Take a Snaps&hot                        Ctrl+Shift+Alt+H
```

Always present, every item greyed out when nothing playing has video. A menu
that appears and disappears changes the shape of the menu bar, and the menu bar
is navigated by position.

#### One item moves out entirely

`Listening Stati&stics... (Ctrl+Shift+Q)` goes to **View**. It is a report about
past listening, not a control over present listening, and View is where the
other reports already are.

#### The arithmetic

39 items in one menu becomes 17 + 11 + 8 in three, plus one moved to View. The
longest menu anybody has to arrow through drops from 39 to 17, and each of the
three answers one question rather than three.

**No keyboard shortcut changes.** Every item already advertises its key in its
label, and the accelerator gate enforces uniqueness across the entire menu bar
rather than per menu -- so moving an item between menus is free in muscle
memory and costs only relearning where to look.

Two decisions inside the split worth stating:

- **No separate "Controls" menu.** Play, Rewind and Forward *are* playback.
  Splitting them out would leave the Playback menu with nothing in it.
- **Video is always present, greyed out.** As above.

### 4. One startup setting

A single checkbox in Preferences: **"Open Browse Stations at startup."** Off by default.

When it is on, Radio opens the main window as usual and *then* opens Browse over it. It does not replace the main window. Closing Browse must leave you somewhere real rather than nowhere.

This is deliberately not a general "which window opens" picker. A setting that changes where you land is expensive for somebody driving by keyboard: one predictable place every launch beats a choice made months ago and half-remembered. Browse is already one key away on Ctrl+B, so the checkbox is a convenience, not a fix.

### 5. Go To: one key for every place in the app

**The problem is not reach, it is recall.** Almost every destination already has
a key -- Browse Ctrl+B, Recordings Ctrl+G, Manage Favorites Ctrl+Shift+M, Player
Ctrl+Shift+G, Song History Ctrl+Shift+H, Downloads Ctrl+Shift+J, Statistics
Ctrl+Shift+Q, Preferences Ctrl+comma. That is eight chords to hold in your head,
and holding eight chords is the actual cost.

The Window menu (Ctrl+Tab, Ctrl+1..9) does not solve it either, for a specific
reason: **it renumbers.** It lists windows that are *open*, in the order they
opened, so Recordings might be 3 today and 5 tomorrow -- and if it is not open,
no number reaches it at all. Position can never become memory.

**Ctrl+G opens a Go To popup.** A short, numbered list of places, open or not:

```
Go To

  1. Favorites                  (this window)
  2. Browse Stations            Ctrl+B
  3. The Player                 Ctrl+Shift+G
  4. Recordings
  5. Downloads                  Ctrl+Shift+J
  6. Manage Favorites           Ctrl+Shift+M
  7. Song History               Ctrl+Shift+H
  8. Listening Statistics       Ctrl+Shift+Q
  9. Find Stations              Ctrl+F
  0. Preferences                Ctrl+comma
```

**Ten positions, numbered 1 through 9 and then 0** -- the number row, in the
order your hand meets it, with 0 sitting where a tenth key would be. Ten is the
ceiling because that is where the number row ends: an eleventh entry would have
no key, and a menu where some rows have a number and others do not is worse than
a shorter menu.

The default fills all ten. **Find Stations** at 9 because searching for a
station and browsing to one are different activities that people reach for
about equally, and Browse already has 2. **Preferences** at 0 because settings
belong at the end of a list, and 0 is where a hand goes last.

*(An earlier draft left 9 and 0 empty "so an upgrade cannot renumber you". That
reasoning was wrong, and worth recording as wrong: a destination added in a
later release lands in the **not-in-the-menu pool**, never in the menu itself,
so it cannot renumber anything whether or not there are empty slots. The pool is
the protection. Empty slots bought nothing and cost two positions.)*

**The pool** -- destinations available to add, not in the menu by default:
Scheduled Recordings, Station Catalog Status, Audio Health, Keyboard Shortcuts
Sheet, What's Playing. Somebody who records on a timetable will very reasonably
want Scheduled Recordings at 4 and Statistics gone; that is exactly what the
settings dialog is for.

`Ctrl+G` and `Ctrl+Shift+G` (Go to Player) become a pair, which is the kind of
mnemonic that survives without being written down.

#### The key change this forces, and how it resolves

Ctrl+G is Recordings today, so Recordings has to move. **Ctrl+R is not
available for it: Ctrl+R is Record Now / Stop Recording**, which is both the
more frequent action and the more natural mnemonic. Taking it would be a
downgrade.

**Recordings gives up its dedicated chord and is reached through Go To.**

That is not a loss dressed up as a decision -- it is the distinction this whole
design runs on. **Recordings is a place. Record Now is an action.** Places live
behind Ctrl+G; actions keep their own keys. Recordings stays on the Record menu
with its label, it stays in Go To at a position you choose, and anybody who
wants a chord for it can bind one in the Keyboard Manager, which already exists.

The alternative was Ctrl+Shift+Alt+R, which is free and is a four-key chord
nobody would press twice.

#### Rules

- **Press the number to go.** Arrows and Enter work too, but the number is the
  point: Ctrl+G then 4 is two keystrokes and no reading.
- **Each row shows its own direct key**, where it has one. The popup is a
  teaching surface as well as a shortcut: somebody who uses Ctrl+G 2 for a month
  learns Ctrl+B by reading it every time, and graduates off the popup.
- **Already open means raise, not open again.** No second Recordings window.
- **Escape returns focus exactly where it was**, to the control and the
  character -- the same contract the player panel already keeps.

#### The list is yours to configure

Fixed numbering is what makes this worth having; **fixed does not mean chosen by
us.** A list you arranged is more memorable than one we arranged, because you
put the thing you use most at 1.

**Go To Settings...** (from the popup itself, and from View) uses the two-list
shape Choose Columns already established:

- one list of what is in the menu, in order, with Move Up / Move Down
- one list of what is not, with Add / Remove between them
- a line underneath reading out what the menu will say, so you can hear the
  result before pressing OK
- **hidden means absent, not last** -- the same rule as Choose Columns, because
  the only way to stop hearing an entry is for it not to be there

Constraints worth stating:

- **Ten entries maximum**, numbered 1-9 then 0. Adding an eleventh is refused
  with a sentence that says the number row is full and which entry to remove
  first -- not a disabled button that says only no.
- **At least one entry**, refused with a sentence saying why rather than a
  disabled button that says only no.
- **An unknown id in a saved layout is dropped on read**, and a destination
  added in a later release appears at the end rather than renumbering what you
  already learned. A layout from an older version must never renumber the
  entries you have memorised.

**This is the third instance of one pattern**, and it should not become a third
implementation. `core/quick_actions.py` orders actions; `core/media/list_columns.py`
orders columns with a hidden set, a tolerant loader and a repair pass, shared
between Radio and Cast. Go To needs exactly that: an ordered list of ids, a
hidden set, a catalogue supplied by the app, and a loader that survives ids it
does not recognise.

The recommendation is to lift the generic core out of `list_columns.py` -- it is
already app-independent and already does everything needed -- and have columns
and Go To sit on it as two catalogues. The reorder dialog is the expensive part
and it is the part most worth sharing; a listener who has arranged their columns
should meet the same window, with the same keys, when they arrange their Go To
menu.

#### What this is not

Not a command palette. Ctrl+Shift+P still runs commands and still filters by
typing. This is **places, not verbs**, and it deliberately never asks you to
type. For a screen-reader user a filtering search box is the most expensive way
to reach a destination you already know the name of.

It also appears as `&Go To...  Ctrl+G` in the View menu, because a key nobody can
discover is a key nobody uses.

## What this does not touch

- Favorites data, and the favorites tree's own context menu and keys (Enter, Delete, F2, Shift+F10)
- The status bar and F6
- The player window's internal layout, beyond gaining the favorite toggle
- The Record menu
- Every existing keyboard shortcut in the app

## How it gets checked

Existing gates cover most of it:

- The **menu accelerator gate** (`tests/unit/ui/test_menu_accelerators.py`) fails on any duplicate or unparsable key across the whole menu bar. It covers the three-way split and the new Ctrl+Shift+F without any new test being written.
- The **accessible-name inventory** covers the new Mute toggle.

New tests worth writing:

1. The main window exposes exactly the intended controls -- so a button quietly reappearing is a failing test, not a slow drift back to today.
2. "Add the playing station" is reachable from both the Station menu and the player window, and both run one handler.
3. The Video menu exists and is disabled rather than absent when nothing playing has video.
4. The startup checkbox opens Browse *over* the main window, and closing Browse leaves the main window focused.
5. The now-playing control is read-only, is reachable by Tab, does not swallow
   Tab, is not rewritten when its text has not changed, and is not rewritten at
   all while it holds focus.
6. The field omits the track line entirely when there is no track, rather than
   showing a placeholder.
7. The Go To numbering does not depend on which windows are open -- the
   stability is the feature, so a test that pins it is the feature's test.
   Separately: a saved layout from an older release, missing a destination added
   since, must not renumber the entries already in it.
8. Go To raises an already-open destination rather than opening a second copy,
   and Escape restores focus to the exact control it was summoned from.
9. Position 10 is reachable by pressing 0, and an eleventh entry is refused with
   a sentence rather than silently dropped.

## Files this touches

| File | Change |
| --- | --- |
| `quill/apps/radio.py` | Main window layout: remove five buttons, add Mute, swap the now-playing StaticText for a read-only TextCtrl. Station menu gains the favorite toggle. Playback menu splits three ways. |
| `quill/apps/radio_video_menu.py` | The video submenu becomes a top-level menu, always present, disabled when there is no video. |
| `quill/ui/radio/player_panel.py` | Gains the "Add/Remove Playing Station" button. |
| `quill/apps/radio_preferences.py` | Gains the "Open Browse Stations at startup" checkbox. |
| `quill/ui/radio/go_to_dialog.py` (new) | The Go To popup: numbered list, number keys, raise-if-open, focus restore. |
| `quill/core/radio/go_to.py` (new) | The destination catalogue and the saved layout, on the shared ordered-list core. |
| `quill/core/media/list_columns.py` | Generic core lifted out so Go To and Choose Columns share one implementation. |
| `quill/core/app_keymaps.py` | `radio.recordings` loses Ctrl+G; Go To takes it. `radio.record_toggle` keeps Ctrl+R. |
| `quill/core/radio/history.py` | Gains the persisted flag behind that checkbox. |
| `quill/core/app_keymaps.py` | Ctrl+Shift+F for the favorite toggle. |
| `standalone/radio/CHANGELOG.md`, `docs/release-notes-*.md` | Say plainly what moved and where it went. |

`radio.py` is already at its GATE-11 ceiling. Removing five buttons frees more
than the menu split and the new field cost, so this should ratchet the budget
**down** rather than need a rebaseline -- but if the arithmetic goes the other
way, the menu construction is the natural thing to extract into a module of its
own rather than raising the number.

## Risks

- **Relearning.** Anybody who reaches for the Play button will not find it. The keys and menu items are unchanged, and the release notes have to say plainly what moved and where it went.
- **The empty landing page.** With no favorites and nothing playing, the main window is a heading, an empty tree, Mute and Volume. That is thin. The first-run flow covers a genuinely new user; somebody who deleted all their favorites is the case to check by hand.
- **Scope.** This is four changes that share a rationale, not one change. They can ship separately, and probably should: the menu split and the Mute button are low-risk and independent; the button removals are the part people will notice.

## Suggested order

1. Add Mute to the main window (smallest, fixes a real asymmetry on its own)
2. Split the Playback menu three ways
3. Add "Add Playing Station to Favorites" to the Station menu and the player window
4. Remove the five buttons from the main window
5. Add the startup checkbox
6. Add the Go To popup on Ctrl+G, then its settings dialog

Steps 1-3 and 6 are additive and safe to ship on their own. Step 4 is the one
that changes what people see, and it depends on step 3 having landed first. Step
6 is independent of all of them and could go first if it is the part you want
soonest -- it is the only item here that adds a capability rather than moving
one.

## The one call made without a strong opinion

**What's Playing? and Song History stay in Playback.**

They are metadata rather than transport, so View is a defensible home for them
and a tidier one. They stay because they are where people have found them for
three versions, and because they answer a question you ask *while listening* --
which is what the Playback menu is for. Moving them buys neatness and costs
relearning, and this design already spends relearning on the button removals.

Reversible in one line if it turns out to read badly.

## What implementation changed

Two decisions in this document did not survive contact with the codebase, and
the codebase was right both times.

**Recordings could not give up its key.** The design said it would be reached
only through Go To. The menu-accelerator gate refused: *every enabled menu item
must advertise a keyboard route*, which is a rule rather than a preference, so
"reached only through Go To" was never actually on the table. Recordings takes
**Ctrl+Shift+R** from Restore from Backup instead, which moves to
Ctrl+Alt+Shift+W. Frequency wins the shorter chord, and nobody restores a backup
by muscle memory.

**A key that looked free was not.** `Ctrl+Alt+Shift+B` read as unclaimed by a
plain text search and is in fact Show Status Bar, spelled `Ctrl+Shift+Alt+B` --
the same chord, a different spelling. That is exactly the bug fixed earlier the
same day, and the fix caught it. Candidate keys are now checked with
`keymap_query.canonical_binding`, never by grep.

**GATE-11 shaped the module layout.** `radio.py` hit its ceiling four separate
times, and every one was resolved by extraction rather than by raising the
number: `radio_now_playing.py` (the readout and its two guards),
`radio_favorite_toggle.py` (the one pair of facts every door onto "save this
station" reads), `radio_audio_menu.py` (the Audio menu's remembered
preferences), and `radio_go_to.py` (the command and the destinations that had no
method of their own).
