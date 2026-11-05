# Chapter 11: Accessibility, speech and braille

This chapter is about how QUILL talks to you, how it looks, and how it works
with your braille display. You will learn how to ask QUILL what it knows, how
to make it chattier or quieter, how to make the text the size you need, and
what its sounds mean. Braille readers and transcribers will find braille files
covered page by page, and anyone preparing documents for other people will
find GLOW, the accessibility checker built into QUILL.

## Asking QUILL what it knows

Your screen reader tells you what is under the cursor. What it cannot tell
you is what QUILL just did on its own, or what kind of document you have
landed in. Only QUILL knows those things, so QUILL has commands that say them.
You will find these in the **View** menu.

### What Is This Document? (Alt+Shift+F1)

Press `Alt+Shift+F1` to hear the shape of the document, not its file name
(the title bar already has that). QUILL tells you how long it is, how many
headings and list items it has, and whether it is read-only. Think of it as a
quick glance at the page before you start reading.

An empty document says it is empty. That matters, because an empty document
and one that failed to load sound exactly the same, and you need to know
whether to start typing.

### What Changed? (Alt+Shift+F2)

Press `Alt+Shift+F2` to hear what the last command did to the text. Sort
Lines, Remove Duplicate Lines, Change Case and thirty other commands rewrite
the document while your screen reader says nothing. This tells you what
happened without reading the whole thing again.

### Undo and Say What Changed (Alt+Shift+F3)

Press `Alt+Shift+F3` to undo and then hear what was taken back, or hear that
there was nothing left to undo. An ordinary `Ctrl+Z` is silent in both cases,
so you cannot tell them apart by listening.

### Repeat Last Announcement

Speech is gone the moment it finishes. **Repeat Last Announcement** says the
last thing again. It has no key out of the box; run it from the Command
Palette (`Ctrl+Shift+P`) or give it a key of your own.

### Speak Status Bar

**Speak Status Bar** reads out the latest message on the status bar, which is
handy when QUILL wrote something there without saying it. Like Repeat Last
Announcement, it is in the Command Palette and has no key until you give it
one.

> **QUILLBee's tip:** Missed more than one line? Press `Alt+Shift+E` to open the
> Spoken Echo and read the last twenty announcements at your own pace.

## Verbosity and Announcements

You decide how much QUILL says, and when. It can be as quiet or as talkative
as you like. Open **Verbosity Preferences** from the Command Palette: press
`Ctrl+Shift+P` and type "verbosity". You can also give it a key of your own in
the Keyboard Manager.

QUILL speaks alongside your screen reader. It does not replace it, so it never
repeats your typing echo or punctuation, which your screen reader already
looks after.

### Profiles

A profile sets how talkative QUILL is overall. Pick one of four:

- **Beginner** gives full context for every action.
- **Normal** is informative, and it is the default.
- **Expert** leaves out routine confirmations. Errors are always spoken.
- **Quiet** turns off speech and earcons, leaving braille and the on-screen
  status bar.

QUILL tells you when you switch profiles.

### Channels

Choose which channels carry announcements: Speech, Braille and Sound.
**Visual** (the status bar) is always on and cannot be turned off, so the
on-screen status of an action is never lost.

### Quiet Mode and Meeting Mode

**Quiet Mode** silences speech and earcons, which is handy in a meeting or a
shared room. **Meeting Mode** quiets sound further. A `[Q]` or `[M]` indicator
shows when one is on, and the status bar keeps updating either way. **Undo
Verbosity Change** steps back your last verbosity change.

Each has a key that starts with the QUILL key: `Ctrl+Shift+Grave` then
`Shift+Q` for Quiet Mode, `Ctrl+Shift+Grave` then `Shift+M` for Meeting Mode,
and `Ctrl+Shift+Grave` then `Shift+Z` for Undo Verbosity Change. You can also
run them from the Command Palette, or set your own keys in the Keymap Editor.

### Fewer repeats, no floods

Two settings under **Settings > Accessibility and Announcements** keep speech from piling up.

- **Collapse repeated announcements** (on by default) stops QUILL saying the
  exact same thing again when it repeats within a moment, for example when you
  hold a key at the top or bottom of a list.
- **Announcement budget (per 5 seconds)** caps how many announcements are
  spoken in a burst. 0 means no cap.

Both affect only what is spoken. The status bar still shows every update, so
nothing is hidden.

### Trimming specific cues

Two more toggles under **Settings > Accessibility and Announcements** shape what QUILL says.

- **Announce entering and leaving dialogs** (off by default) speaks "Entered"
  and "Exited *name* dialog" as dialog boxes open and close. It is off because
  your screen reader already announces dialogs and reads their titles. Turn it
  on if you like the extra cue.
- **Announce indentation depth on Tab** (on by default) makes Tab and
  Shift+Tab speak the new depth, such as "4 spaces" or "1 tab", instead of
  "Indented lines".

Both affect only speech. The status bar still updates.

### The Spoken Echo (Alt+Shift+E)

Speech flies past. An indent depth, a formatting description, a save result or
a "no matches" is gone the instant it is spoken. The **Spoken Echo** remembers
the last twenty things QUILL said and shows them, newest first, in a read-only
window. You can arrow through it line by line, review it by character, select
text and copy it.

Open it any time with `Alt+Shift+E`, or from **Help > Show Spoken Echo**. It
works after any announcement, even one from an ordinary editing key such as
Tab. So you can hear "8 spaces", then open the Echo to read and copy it. The
Echo only records what QUILL speaks, never your typing. If you would rather
QUILL kept no record at all, turn off **Settings > Accessibility and
Announcements > Keep an announcement history**: the list is cleared, nothing
new is added, and the Echo tells you the history is off.

If you are used to pressing a screen reader's reporting command twice, you can
do the same here. Double-press an informational command (Describe Formatting,
Document Summary, Context Help or Announce Contrast) and the Echo opens,
instead of the same line being spoken again. `Alt+Shift+E` always works. The
double-press can be turned off under **Settings > Accessibility and
Announcements > Double-press to show the Spoken Echo** (on by default).

### Per-action templates

If you want to go further, you can edit exactly what each action says. Use
tokens like `{line}` and filters like `${ordinal:line}`, with live checking and
a preview as you type. Save your templates to a library, share them as
`.quill-verbosity-profile.json` files, or install a QUILL Verbosity Pack
(`.qvp.json`). These are all data files, never code.

### Preview Lab and History

The Preview Lab lets you hear how a profile sounds against sample situations
before you commit to it. History lets you review, replay and copy recent
announcements, and ask "why did QUILL say that?" about any of them.

### Safe Mode

If a custom setup ever misbehaves, Safe Mode brings back the built-in
announcements without deleting your customizations.

### QUILL's own voice

When you run a screen reader, QUILL speaks through it. QUILL also has its own
built-in voice (Windows SAPI 5), used only for people who do not run a screen
reader. If that voice ever fails to start while your screen reader is doing
the talking, QUILL does not interrupt you about it; it just makes a quiet note.
If you do want QUILL's own voice and it did not start, close QUILL and open it
again; it tries the voice once each time it starts. (Some older messages call
this "Retry TTS Engine", but there is no such menu item in this release.)

### What QUILL says when it starts

At startup QUILL speaks only one line, `QUILL Ready`. Other startup messages,
such as the Document Guardian activation cue and the screen reader it
detected, go to the status bar, so you can still see them, while your screen
reader stays quiet. Two settings under **Settings > Accessibility and Announcements** control
startup speech:

- **Speech channel (verbosity)** is the master switch. When it is off, every
  spoken announcement from built-in startup events and Quillin extensions is
  silenced, and the status bar keeps the same text. It is on by default so a
  new user hears `QUILL Ready`. Turn it off for a completely quiet start.
- **Speak screen-reader detection result at startup** speaks the line
  `Detected screen reader: <name>. Adaptive hints enabled.` once the check
  finishes, but only when the speech channel is also on. The status bar always
  shows the result.

Document Guardian has its own switch for its start and stop cue. Open
**More Preferences > Document Guardian > Lifecycle Announcements** and turn on
**Speak activation and deactivation cues** to hear `Document Guardian is now
active.` when it starts and `is now inactive.` when it stops. It is off by
default, and the status bar still records every time it is turned on or off.

### More on the Accessibility and Announcements page

The rest of the **Accessibility and Announcements** page in Settings:

- **Announcement verbosity** is how chatty spoken status messages are overall:
  **Minimal**, **Normal** (the default) or **Verbose**.
- **Announce search and navigation wrap** says so when a search or a move
  goes past the end and starts again at the other end.
- **Announce word and character counts** speaks a count when you ask for one.
  Turned off, the count still goes to the status bar.
- **Announce mode entry and expiry** says when a mode such as Quick Nav or
  the QUILL key starts or runs out.
- **Announce spelling results** speaks spelling feedback such as how many
  misspellings were found.
- **Spoken punctuation level** is how much punctuation those announcements
  include: **None**, **Some** (the default), **Most** or **All**.
- **Announcement throttle (milliseconds)** is the shortest gap between two
  spoken announcements, up to two seconds. The default, 0, means no gap.
- **Record announcement trace** keeps a log of QUILL's announcements for
  support. It never records your document. Off to begin with.
- **Speak startup readiness and theme contrast announcements** speaks the
  "Ready" tip after QUILL starts and the contrast ratio after you change
  theme. Off to begin with; both still appear on the status bar.
- **Say what list the cursor is in** is the list announcement described in
  Chapter 6. On to begin with.
- **Enable sound notifications** plays the short sounds for editing events
  such as an abbreviation expanding, a save or a search. On to begin with.
- **Sound pack path** picks a sound pack with **Choose Sound Pack...**. Leave
  it blank for the Ink pack that comes with QUILL.
- **Sound notification volume** runs from 0, silent, to 100. The default is
  80.
- **Silenced sound events** is the list of sounds you have turned off. The
  Sound Scheme window, in Chapter 7, is the easy way to change it.
- **When a command does something, give me** is how a copy, a paste, an undo
  or a started selection reports back: **Play a sound** (the default),
  **Speak the action**, **Both a sound and speech** or **Neither**. Speaking
  the action is a good choice while you are still learning the sounds.
- **When a search finds nothing, give me** offers the same four answers, just
  for a search that finds nothing. It is separate because `F3` is pressed
  again and again, and hearing "Not found" every time wears thin. The status
  bar says it whichever you pick.
- **Announce "Generating preview, please wait" for slow voice previews** is
  the heads-up described under Choosing a voice, in Chapter 8. On to begin
  with.
- **GitHub check: how often (minutes)**, **GitHub check: play a sound on each
  check** and **GitHub check: let results interrupt speech** decide how often
  QUILL looks for GitHub notifications (every 15 minutes to begin with), and
  whether you hear each check and its results straight away. **Weather
  check** and **Podcast check** settings on the same page work the same way
  for weather alerts and podcast feeds, and **Check podcast feeds in the
  background** turns podcast checking on. It is off to begin with.

## Appearance

QUILL is built so that people with low vision can see it as well as hear it.
You can make the text larger, choose the typeface, check contrast and switch
themes.

### Contrast and theme

You can check contrast, switch to dark mode, or follow the colours Windows
uses. If you need a low-vision setup you can rely on, choose the one that
works for your eyes and QUILL will keep to it.

To check the current colours, press the QUILL key and then `Shift+C` (**Announce
Contrast Ratio**). QUILL works out the contrast between the editor's text and
its background and gives it a grade, for example "Contrast ratio: 15.3:1,
WCAG grade: AAA (excellent)". QUILL always says it out loud, because you
asked, and puts it on the status bar too. (**Speak startup readiness and theme
contrast announcements** only covers what QUILL says on its own after it starts
or after a theme change.)

If you use a Windows high contrast theme, leave QUILL on the system theme and
it uses that theme's colours, light or dark, exactly as you chose them.

### Text looks blurry, or a window is the wrong size

QUILL scales itself for each monitor. Text stays sharp at 125, 150 or 200
percent, and when you move a window to a monitor with different scaling;
windows and list columns keep their proportions. If a window looks wrong at
your scaling, you can turn this off to see whether it is the cause. Search
Windows for "Edit environment variables for your account", add a variable
named `QUILL_DPI_UNAWARE` with the value `1`, and start QUILL again.
Windows then stretches it the old way, so text is blurrier. Delete the
variable to put scaling back, and tell support what you saw.

### The size and face of the text

Three keys change the size of the text, and they are the ones you already
know from Notepad, your web browser and QUILL Lite.

| Key | What it does |
| --- | --- |
| `Ctrl+=` | Increase Text Size, one point |
| `Ctrl+-` | Decrease Text Size, one point |
| `Ctrl+0` | Reset Text Size to the default (12 point) |

Each time you press one, QUILL says the new size, such as "14 point", so you
always know where you landed. The size runs from 6 to 72 points and is saved,
so tomorrow the editor opens the way you left it today.

To choose the typeface and size together, use **Format > Font...**
(`Ctrl+Alt+F`). It opens the standard Windows font window, which every Windows
screen reader already reads well.

Your choice of typeface is about how you read, not about the file. Choosing
Consolas at 18 point changes what is on your screen and nothing in the
document. The typeface is never saved into the file, just as dark mode is not.
A colleague who opens the same file sees their own font, and you see yours.

The size applies to every open tab, not only the one in front of you. It also
stays put when you change theme.

### Rich text documents work a little differently

In a Word or RTF document, the point sizes are part of the heading structure.
A Heading 1 is large because it is a Heading 1. If `Ctrl+=` made every bit of
text bigger, your headings and body text would end up the same size, and
heading navigation and the headings list, which rely on those sizes, would
stop working well.

So in a rich text document the same three keys zoom the view instead. The
text on screen grows or shrinks by the same amount, the document itself is
not touched, and the headings keep their sizes. `Ctrl+0` takes you back to
100 percent. You do not need to know which kind of document you are in: the
keys are the same, and you get what you asked for.

To change the face and size of text you have selected in a rich text
document, use **Format > Font for Selection...** (`Ctrl+Shift+F`). That one is
a real edit to the file. In a plain or Markdown document it declines and tells
you where to go instead. `Ctrl+Shift+F` is Word's key for Font. If you used
it for Search in Files in the past, Search in Files is now on
`Ctrl+Alt+Shift+F`, as **Edit > Search in Files...**.

### The text settings, if you would rather type them

Both are on the **Editing** page of Settings, as **Editor font** and **Editor
text size (points)**; or type "font" in **Find a setting**.

- **Editor font** (`font_name`) is the typeface. Leave it empty to use
  whatever Windows picks, which is right if you have never chosen one.
- **Editor text size (points)** (`font_size`) runs from 6 to 72, default 12.
  If a value in your settings file is outside that range, QUILL uses the
  nearest size it allows instead of refusing it, so the editor still opens in
  a readable size.

QUILL Lite uses the same two setting names, so a settings file carried between
the two means the same thing in both.

## Accessibility

These tools help you check QUILL itself and the document you are working on,
and keep useful information within reach of the keyboard.

### Moving between regions (F6)

Press `F6` to move from the editor to the next major region of the window, and
`Shift+F6` to move back. QUILL announces each move in the same way every time.

### Checking where you are and what you have

Earlier versions had an Accessibility submenu on the Tools menu, with an interface audit,
a tab-order snapshot, a contrast validator and a link catalog. That submenu
is not in this release. What it did is covered by these instead:

- **Navigate > Speak Status Summary** (the QUILL key, then `Q`) tells you the
  document's name, where it is saved, whether it has unsaved changes and its
  encoding. The status bar, described next, has the line and column.
- `Ctrl+Shift+Y` (**Say Selected**) reads what is selected.
- The QUILL key, then `Shift+C` (**Announce Contrast Ratio**), grades the
  editor's colours (see Contrast and theme, above).
- For your document's own accessibility, use the GLOW review described later
  in this chapter, or **AI > Accessibility Tune-Up...** once **AI > Show
  advanced AI features** is checked.

### The status bar

QUILL's status bar is something you can move into and use, not just look at.
It keeps useful information close and reachable from the keyboard.

### The page indicator

The status bar has a **Page** cell for every document, on by default, next to
your line and column.

For PDFs this is an exact count. QUILL knows the real page boundaries from the
file, so it reads, for example, "3 of 12."

Plain text, Markdown and most Word documents have no real pages until you
print or export them, because page breaks depend on the font, margins and
paper size. For these, the Page cell shows an estimate based on the word
count, such as "~3 of ~12 (estimated)." The tilde and the word "estimated"
always come together. A page number without them is a real count; with them,
it is QUILL's best guess.

If your pages usually hold more or fewer words, change **Settings >
Navigation and QUILL Key > Estimated words per page** (default 300, range
150-600).

To jump to a page, press **Go To** (`Ctrl+G`), or press Enter on the Page
cell. Choose **Page** at the top of the window, then pick from the list or
type the number. For PDFs the rows are exact page numbers. For everything else
each row reads `~4 (estimated)`, so you know which kind of jump you are making.

Braille (BRF) documents have their own, more detailed page system (see
[Braille mode](#braille-mode)) and do not show this Page cell.

## Sound notifications and earcons

QUILL can play short sounds, called earcons, at moments that matter while you
edit. Your screen reader stays free for the text, and the sound tells you
"something happened". Sound is optional and off by default for most events,
and it never replaces speech.

### Sound packs and events

- **Sound packs (QSP).** A sound pack is a folder (or a `.qsp` zip) of WAV
  files with a `manifest.json` that says which sound goes with which event.
  QUILL comes with the **Ink** pack and uses it whenever you turn sound on. On
  the first-run **Keyboard and Sound** page, the **Sound pack** control is a
  dropdown of the packs that come with QUILL. It starts on QUILL's own pack,
  so turning sound on always gives you working earcons.
- **Per-event control.** Open **Tools > Reading and Dictation > Sound
  Scheme...** to turn single events on or off. Events are grouped into
  Earcons, Compare and (when an indent-tone pack is loaded) Indentation tones,
  so you can keep, say, the save and search cues and silence the rest.
- **QUILL's sounds on or off.** **App Sounds** (in Reading & Dictation,
  Alt+Shift+M) turns QUILL's own sounds off or back on, and plays a short
  "off" or "on" cue so you know which way it went. **App Sounds Play On...**
  in the Sound Scheme window chooses the sound card they play on. The
  **Sound notifications** setting still silences every QUILL app at once.
- **Indentation tones.** In code and other indented text, QUILL can play a
  tone as the caret crosses indent levels. The tone rises as you go deeper and
  falls as you come back out. Pick a scale (pentatonic, whole-tone, diatonic
  or chromatic) in the **Indentation tones** setting, or leave it Off. Blank
  lines stay silent and keep the previous level.
- **Compare cues.** With a sound pack on, comparing documents plays its own
  cues for opening and closing a comparison, moving to the next or previous
  difference, and reaching the first or last difference. Comparing documents
  is covered in Chapter 8, Reading, reviewing and listening.
- **Numbered slots have their own notes.** The twelve Copy Tray slots and the
  ten quick-bookmark slots each play their own pitch when you copy, paste, set
  or jump. Copy Tray slots are soft marimba taps and bookmarks are brighter
  chirps, so you know which family it is straight away. After a while, "slot
  seven" is a note you recognise rather than something you wait to hear.
- **Progress you can hear.** Long downloads and installs play a short blip
  every 5 percent, rising in pitch as they get close to done. The 25, 50 and
  75 percent marks have a touch of harmony, and 100 percent ends with a small
  two-note finish. A sound never talks over your screen reader the way a
  spoken percentage does. QUILL still speaks the quarter marks.
- **Selection and boundary cues.** Starting a selection with `F8` plays a
  rising two-note sound, and finishing it plays the same in reverse. The very
  top of the document gives a high tick, and the very end a low thud.
- **The other apps have their own sounds.** Quill Radio and Quill Weather
  mark their own moments (connecting, a stall, a new weather alert) through
  the same Sound Events system, and you can turn each one off in the same
  place. Each app's own user guide lists its sounds.
- **Keep the sound device awake.** Some USB and Bluetooth audio devices go to
  sleep after a few silent seconds and clip the start of the next sound. If
  the start of your earcons or speech gets cut off, turn on **Keep the sound
  device awake** (in Settings, search "keepalive"). QUILL then plays a silent
  clip every 20 seconds so the device stays awake. Off by default.

### Choosing between a tone and words

Some moments can be marked with a sound or with a sentence. Which you want
depends on how long you have used QUILL. A new tone means nothing until you
learn it, but once you have, hearing "Copied" on every `Ctrl+C` gets old
fast. So you choose.

- **Action feedback** (`action_feedback`) covers the moments where a key did
  something and your screen reader says nothing: cut, copy, paste, delete,
  undo, redo, and starting a selection with `F8`. Choose **Play a sound** (the
  default), **Speak the action**, **Both a sound and speech**, or **Neither**.
  When a moment has a number worth hearing, such as "Pasted 1,234 characters
  as plain text" or "Selected 412 characters, 68 words", the number is always
  spoken, because a tone cannot carry a count. **Neither** stays silent but
  still writes to the status bar, so you can read what happened.
- **Find: nothing found** (`find_not_found_feedback`) offers the same four
  choices for when a search finds nothing. It is a separate setting because
  you press `F3` again and again, and "Not found" spoken every time soon gets
  wearing. It also starts on the tone alone.

If you choose a sound for a moment your sound pack has no sound for, QUILL
speaks instead, so you always get one or the other. Turning off a single event
under **Sound Events...** is different: that is you asking for quiet, and it
stays quiet.

### Wrapping at the ends of a search

**Wrap around when searching** (`wrap_find`) decides what happens when Find
Next reaches the end of the document, or Find Previous reaches the start. When
it is on (the default), the search carries on from the other end, and a wrap
sound tells you it did. When it is off, the search stops and tells you where:
*"No more matches. Reached the end of the document, and wrapping is off."*

The two messages need different fixes. "Not found" means change what you are
searching for. Reaching the end means go to the other end and search again.
The setting works in both directions, in QUILL and QUILL Lite alike.

### When a word cannot be added to a dictionary

**Add to This Document Only** and **Add to This Project** save a small
dictionary file beside your document. A document you have not saved yet has
nowhere to put one, so QUILL tells you and says what to do: *"Cannot add
"Bhattacharya" to this document only until the document is saved. Save it, or
add the word to your personal dictionary instead."* Your **personal
dictionary** always works, saved document or not, because it lives with your
settings, not with the file.

### Background checks

QUILL quietly keeps an eye on a few things for you: a watched folder, the
weather, and your GitHub account if you use it. Each of these has the same
three controls, so once you have set one up you know them all. Find them in
Settings by typing the monitor's name in **Find a setting**, or "tick",
"interrupt" or "check".

- **How often it checks.** Watched folders count in seconds, so a file you
  just dropped in is noticed while you are still there. Feed and account
  checks count in minutes, since asking a server every few seconds does no
  good. A value of 0 or less is raised to that monitor's minimum.
- **Whether each check makes a sound.** Turn on **Play a sound on each
  check** to hear a short tick every time that monitor looks. This is not news
  that something happened; it shows the watcher is still running, so silence
  means it has stopped. It is off by default for every monitor. Turn it on for
  the one or two you really want to hear working.
- **Whether a result interrupts speech.** Turn on **Let results interrupt
  speech** and that monitor's announcements cut in over whatever is being
  spoken. Leave it off (the default) and they wait their turn, so a new result
  never cuts a sentence in half while you are reading. Some people want the
  weather to interrupt and the watched folder to wait, and some want the
  opposite. Real errors always interrupt, whatever the setting.

QUILL sums up your choices in one sentence, for example: *"Checks every 15
minutes, ticks audibly, does not interrupt speech."*

### Every sound in the Ink pack

The Ink pack has sounds for these events: `quill_key_pressed` (the QUILL key
is waiting for its next key), `abbreviation_expanded`, `abbreviation_deleted`,
`snippet_inserted`, `autocomplete_accepted`, `document_saved`,
`document_created`, `search_found`, `search_not_found`, `search_wrapped`,
`heading_jumped`, `table_entered`, `browse_mode_on`, `browse_mode_off`,
`ai_thinking_started`, `ai_response_received`, `ai_error`,
`transcription_started`, `transcription_stopped`, `ssh_connected`,
`ssh_disconnected`, `error`, `warning`, `sound_on`, `sound_off`, and the five
compare events. Every sound in the pack is different, so two events never
sound the same.

If you make sound packs, you can map any event to any WAV file. The full QSP
format and list of events are in the product requirements document, under
"Sound notifications and QSP sound packs." If you run QUILL from a source
checkout, the `audition_ink_sounds` script in its scripts folder plays the
pack family by family, and adding `--all` plays every sound in it.

## Braille mode

QUILL opens and edits formatted braille files (`.brf`, `.brl`, `.pef` and
`.ueb`) as plain NABCC, also called braille ASCII. If you proofread
transcriptions, you can move through a file the way it is really laid out, in
braille pages and cells, and QUILL tells you exactly where you are.

### Your braille display

QUILL shows text on your display starting in cell 1, and shows a selection
with dots 7 and 8. Two checkboxes on **Settings > Braille Mode** make this
work, and both are on out of the box:

- **Fix braille cell alignment and selection dots (recommended)**
- **Hide editor border (required for braille cell alignment)**. The visible
  border pushes braille output out of cell 1, so it has to go.

Leave both on unless your display has trouble. If you uncheck the border
setting, QUILL warns you first that cell alignment will break. Restart QUILL
after changing either one so every document uses the new setting. If you
remember the old Editor control type and Experimental surface settings, these
two replaced them.

### Opening and saving braille files

Open a `.brf`, `.brl`, `.pef` or `.ueb` file the same way you open anything
else. QUILL reads it as braille text. A UTF-8 byte-order mark is removed if
there is one, and QUILL checks for any character that is not braille ASCII.
Nothing else changes on the way in: what you see is what is in the file.

Saving keeps the file byte for byte. QUILL does not trim trailing spaces or
change line endings, and form feeds (the hard page breaks) are kept. If the
text has characters outside braille ASCII, QUILL still saves them as they are
and gives you one spoken warning that does not stop you, so nothing changes
without your knowing. Open a file and save it, and you get back an identical
file.

### Picking up where you left off

When you open a braille file again, QUILL puts your cursor back where you
were and tells you, for example: "BRF file opened. 87 braille pages
detected. Last position: braille page 12, line 14, cell 31."

Your place, your proofing progress and your notes are kept in a small
companion file next to the braille file. The braille file itself is never
changed. QUILL does not restore your place in Safe Mode or when companion
files are turned off. If the file was shortened somewhere else, your cursor is
placed safely inside it.

### The braille status cell

While a braille file is open, the status bar has a braille cell that updates
as you move. It reads like `BRF Pg 12/87 | Ln 14/25 | Cell 31/40 | Print 7`:
the braille page, the line on that page, the cell on that line, and the print
page. QUILL looks for print page numbers every time you open the file and
every time the page map is rebuilt, so the print page is filled in whenever
the file marks it. When the file has no print page markers, it reads
`Print ?`.

### The Braille menu

Braille commands are under **Tools > Braille**. None of them has a key out of
the box, so nothing clashes with your screen reader or the editor's own keys.
Give them keys in the keyboard customizer, or run them from the Command
Palette.

Every status, navigation and layout command is safe to run on a document that
is not braille: it just says "This is not a braille document". (Remove
Trailing Spaces and Go to Longest Line work on any document's text.)

#### Status

- **Read Status** (follows your status verbosity)
- **Read Detailed Status** (adds the print page, continuation letter, running
  head, proofing state and how sure QUILL is of the layout)
- **Read Current Line and Cell**
- **Read Current Braille Page**
- **Read Current Print Page**
- **Read Progress Summary** (how far through the document you are)
- **Announce Running Head**, **Include Running Head in Status** and **Omit
  Running Head from Status**

#### Navigation

- **Go to Braille Page...** (type a page number), **Next Braille Page** and
  **Previous Braille Page**
- **Go to Print Page...** (type a print page number that QUILL found)
- **Next Print Page Change** and **Previous Print Page Change** jump to where
  the print page changes. Going past the first or last one tells you there are
  no more.

#### Page Tools

- **Insert Braille Page Break** (a form feed) and **Remove Braille Page
  Break** at the cursor
- **Recalculate Page Map** rebuilds the page map after you edit
- **Normalize Line Endings** (a placeholder, not working yet)

#### Proofing

Keep track of your proofreading without ever changing the braille file.

- **Mark Current Page Proofed** or **Mark Current Page Needs Review**, or
  take the mark off again with **Clear Proofing Mark**.
- **Add Proofing Note...** adds a note to the current page.
- **Read Progress Summary** speaks the pages proofed, the pages needing
  review, the last page you proofed, and an estimate of when you will finish.
- **List Proofed Pages...** and **List Pages Needing Review...**. Choose a
  page to jump to it.
- **Export Proofing Report...** saves a plain-text report of it all.

Your progress is kept in the small companion file next to the braille file,
so it travels with the document and never changes it. If the file has not been
saved yet, these commands ask you to save it first.

#### Validation

**Validate BRF Layout** checks the layout of a braille file for ten kinds of
problem: lines or pages that are too long, pages that look stuck (too short),
missing page breaks, mixed line endings, characters that are not braille
ASCII, page numbers that are malformed or missing, gaps or repeats in page
numbering, running heads that do not match, and files in Unicode braille
instead of NABCC. It opens a Warnings List; choose a warning to go to it.

**Next Warning** and **Previous Warning** move through what it found and say
"Warning N of M" with the message. **Warnings Summary** speaks the total and
the most common kinds. Validation only reads the file and never changes it.

#### Repair

These fix the two problems that most often stop a braille file embossing
cleanly.

- **Read Layout Metrics** speaks the numbers in one go: the cell you are on
  and the length of this line; the longest line in the file against your
  cells-per-line limit, with "page width exceeded" when it is over; the
  current and total braille pages; and the longest page against your
  lines-per-page limit, with "page depth exceeded" when it is over.
- **Go to Longest Line** and **Go to Longest Page** take you straight to the
  worst one so you can fix it. A page that is too long usually needs a page
  break where one is missing (Insert Braille Page Break).
- **Remove Trailing Spaces on This Line** and **Remove Trailing Spaces in
  Whole File** clear the trailing spaces behind most page-width problems, and
  keep every line ending and form feed.

The limits come from your **Cells per line** and **Lines per page** settings
under **Settings > Braille Mode**, so the numbers match the page size you are
transcribing for.

### Translating with the QUILL Braille Pack

Translating between print and braille, in either direction, needs the
optional **QUILL Braille Pack** (also called the Universal BRF Pack). It
contains the full catalogue of liblouis braille tables, a set of profiles that
give those tables friendly names, and the translation engine itself.

The pack is not included by default. Without it, the **Translation** submenu
is hidden, so you never meet commands that do nothing. In its place, **Tools >
Braille** has **Download Braille Translation Pack...**, which opens Download
Optional Components with the braille pack already chosen. Press **Download**,
and the Translation submenu is there from then on. With it installed, the
Translation submenu starts with the two commands most people want, then the
detailed sections:

- **Back-Translate to Text (Auto-Detect Code)** is the easy way. You do not
  need to know whether your braille is UEB Grade 2, UEB Grade 1, legacy
  American (EBAE) Grade 1 or 2, or computer braille. QUILL tries a sample of
  the document (or your selection) in every likely code, sees which reads most
  like real English, and uses that one. It tells you what it found, for
  example "Detected UEB Grade 2 (contracted)". If a file is uncontracted,
  QUILL says Grade 1, even though the Grade 2 table would also have worked.
- **Convert BRF File to Document...** takes a braille file on disk straight
  to a readable document. Pick any `.brf` or `.brl` file, and QUILL detects
  its code, back-translates the whole file and opens the result as a draft,
  without your opening the braille file first. The draft is an ordinary
  document, so **Save As** can turn it into Markdown, HTML, Word (`.docx`) or
  plain text.
- **UEB (Unified English Braille)**: Contracted (Grade 2), Uncontracted
  (Grade 1), Translate Selection to UEB, and Back-Translate UEB (which skips
  detection).
- **Standard American English (Legacy)**: Contracted (Grade 2) and
  Uncontracted (Grade 1), using the traditional North American English
  tables.
- **More Languages** is filled in from the profiles in the pack you have
  installed. A language with more than one profile, such as contracted and
  uncontracted, gets its own submenu. German, French, Spanish, Russian, Korean
  and dozens more are there.

Translating to braille opens the result in a new document and tells you how
many braille pages it made. Translating back from braille always opens its
result as a clearly labelled **draft**, because no automatic back-translation
can be trusted completely. If you have text selected, only the selection is
back-translated, which is handy for recovering one passage; otherwise the
whole document is. QUILL tells you which, for example: "Back-translation draft
from selection. N words. Review against the BRF."

Translation runs separately from QUILL, so a translation failure can never
take QUILL down. If it fails, QUILL tells you why and does not open an empty
document. The Translation submenu is also hidden in Safe Mode.

Translation works the same whether you use the installed version, the
portable version or a source checkout. The pack carries its own translation
tool (`lou_translate`, next to the tables), so you do not need to install
liblouis for Python separately. If you do have it, QUILL uses it, because it
is a little faster.

### The Braille Mode page in Settings

Most of the **Braille Mode** page is covered above. The rest:

- **Use form feeds for page breaks** treats the page-break characters in a
  braille file as real page breaks. Leave it on unless the file never used
  them. Turn it off and QUILL counts pages by your page size instead.
- **Calculate pages from geometry**: when a braille file has no page breaks,
  QUILL works out the pages from your page size. Turn this off and a file
  like that is read as one long page. On to begin with.
- **Announce page changes automatically**: turn this on and QUILL says
  "Braille page 5" as your cursor moves onto a new page. If you got there
  with Next Braille Page or Go to Braille Page, you only hear it once. Off to
  begin with.
- **Announce print page changes**: turn this on to hear "Print page 7" when
  you move onto a new print page. Files without print page numbers stay
  quiet. Off to begin with.
- **Announce line overflow**: turn this on and QUILL tells you when a line is
  longer than your Cells per line, for example "Line too long: 45 cells,
  limit 40". You hear it once when you reach the line, or when your typing
  pushes it past the limit. Off to begin with.
- **Include proofing status in status string**: Read Detailed Status tells
  you the last page you proofed and how many pages still need review, from
  the companion file. On to begin with; turn it off for a shorter status.
- **Include continuation in status string**: Read Detailed Status names the
  continuation letter (7a, 7b) when a print page runs on. On to begin with.
- **Write sidecar on save** saves a small companion file next to a braille
  file when you save it, recording the page size and line endings, so other
  tools can pick up where you left off. On to begin with.
- **Include running head in status string** adds the page's running head to
  the detailed braille status, when there is one. Off to begin with.

### Braille files in Convert File

The everyday converter, **File > Convert File**, accepts `.brf` and `.brl`
files too; they appear in its file picker with everything else. Pick a braille
file and any output format (Markdown, Word, HTML, EPUB, plain text and the
rest). QUILL detects the braille code, back-translates and writes the result,
and tells you which code it found. There is no separate braille converter to
look for.

## GLOW Workflows Inside QUILL

GLOW (Guided Layout and Output Workflow) is QUILL's built-in accessibility
checker. It reviews your document for accessibility problems and offers safe,
predictable fixes, and it shows you what it found in plain words, not a
compliance dashboard. Its four commands are on **Tools > Writing and
Language**: **GLOW Audit Document**, **GLOW Audit Selection**, **GLOW Fix
Document** and **GLOW Fix Selection**, once it is turned on in the
Experimental tab as described next.

### Turning GLOW on

GLOW is an **experimental feature** and is off by default while it matures.
To turn it on:

1. Open **Settings > Experimental**.
2. Check **Enable experimental features**, the main switch for the whole tab.
3. Check **GLOW accessibility review and repair (experimental)**.
4. Apply your settings.

The four GLOW rows appear on **Tools > Writing and Language** straight away, with no restart. While GLOW
is off, its commands still show up in the Command Palette, and running one
tells you how to turn GLOW on. Experimental means still being finished, not
unsafe: GLOW always shows you before it changes anything, and it never
touches your original file.

### Auditing a document

- **GLOW Audit Current Document** checks the whole file in front of you.
- **GLOW Audit Selection / Paragraph** checks just the block at the caret.
- **GLOW Audit File...** picks a document on disk (DOCX, PPTX, XLSX, PDF,
  EPUB or Markdown) and checks it in the background. You get a score, a
  grade, and every finding with a suggestion.

The results open as ordinary QUILL tabs you can read, search, compare, or
keep open beside the document. Each finding names the rule, how serious it
is, where it is when that is known, and a suggestion in plain language.

### Fixing a document

- **GLOW Fix Selection / Paragraph** tidies up where you are, in place.
- **GLOW Fix Current Document** makes a fixed version and opens it straight
  away beside the original, so you can compare them. Accept or reject the
  changes knowing exactly what they are.
- **GLOW Fix File...** saves a repaired copy of a document next to the
  original, for example `report-accessible.docx`. The original is never
  changed. QUILL checks the new file name with you first, and then opens an
  audit of the repaired copy so you can see the result.

### What GLOW checks

In the editor, GLOW checks plain text, Markdown and HTML for:

- a missing space after a Markdown heading marker
- headings that skip a level
- vague link text, such as "click here"
- a missing language setting in HTML
- images with no alt text
- tables with no header cells
- indenting with tabs that can cause problems
- dense paragraphs and hard-to-read wording

The optional GLOW engine adds Word, PowerPoint, Excel, PDF and EPUB files
(DOCX, PPTX, XLSX, PDF, EPUB), with a scored and graded report.

### The GLOW engine and updates

The in-editor checks are always there. Checking and fixing those other file
types needs the optional GLOW engine (installed with QUILL's `glow` extra).
When it is missing, QUILL tells you so plainly.

**Help > Check for GLOW Updates...** looks for a newer engine when you ask it
to; it never checks on its own. Downloading needs a separate yes from you,
every download is checked for its signature and checksum, and if an install
fails QUILL goes back to the engine it came with.

### GLOW settings

**More Preferences > GLOW Accessibility** has the engine switch and the optional
features that use the internet: AI alt text, PII redaction, and WCAG language
processing. All of these are **off by default**, and each one asks your
permission every time it is used. Out of the box, GLOW runs entirely on your
own computer.

### Inserting images with alt text

GLOW's audit finds missing alt text after the fact. **Insert > Image...**
stops it going missing in the first place. Before you can insert an image,
you either write alt text that describes it, or check **"This image is
decorative"**. Decorative is right for an image that carries no information,
such as a divider line or a background flourish. It is not a way to skip
describing an image that does carry information.

**Let AI draft the alt text.** If the provider you saved in **Use My Own AI
Key** (`Alt+F2`) has a model that can see images, and you are not in Safe Mode,
the window has a **Suggest alt text with AI** button. It uses that provider,
the one QUILL's advanced AI features use, not the connection chosen in Choose
Your AI. Choose your image file and press it.
QUILL describes the picture and puts the description in the alt text field
for you to read, correct and approve before inserting. AI is fully turned off
in Safe Mode, so the button does not appear there.

**Images that fit a web page.** When you insert into an **HTML** document,
the window adds a **Size and layout** section:

- **Width** and **Height** (optional) let a browser save the space, so the
  page does not jump about while the image loads.
- **Responsive**, on by default, lets the image shrink to fit narrow columns
  instead of spilling over.
- **Caption** (optional) is inserted as a proper `<figure>`/`<figcaption>`,
  so screen readers know the caption belongs to the image.

These options are hidden in Markdown documents, which cannot hold them. There
you get the familiar `![alt](path)`.

For any image already in your document, whether typed by hand, pasted or
brought in from another format, **Tools > Advanced > Describe Image at Cursor** tells you
what a screen reader will hear there: "Image: sunset.png, alt text: a sunset
over the lake," or "Image: sunset.png, alt text MISSING" if it has none.

## What you learned, and where to go next

You can now ask QUILL what a document is and what just changed, set how much
it says and through which channels, and read back anything you missed in the
Spoken Echo. You know how to make the text the size you need, what QUILL's
sounds mean, how to work page by page in braille files, and how to check and
fix a document with GLOW.

To practise, open **Help > Tutorials...** (`Ctrl+Alt+F1`) and try "Decide how
much QUILL says", "Make QUILL the size you need" and "Braille files, page by
page". On the website,
[Make a document accessible with GLOW](https://www.quillforall.org/tutorials/06-make-it-accessible-with-glow.html)
walks through GLOW from start to finish.

Next, Chapter 12, Making QUILL yours, shows you how to set up keys, profiles
and preferences the way you like them.

---

- Previous: [Chapter 10: AI, when you want it](quill-guide-10-ai-when-you-want-it.html)
- Next: [Chapter 12: Making QUILL yours](quill-guide-12-making-quill-yours.html)
- [Contents](../userguide.html)
