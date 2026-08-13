# Quill Inkwell User Guide

Quill Inkwell expands abbreviations in every Windows application. Type a short
word, press space, and Inkwell replaces it with whatever you saved: a phrase, an
email address, a signature, a paragraph of boilerplate, a template with the
caret already in the right place.

It is part of the QUILL family and free, and its abbreviations are the same
abbreviations QUILL's editor expands. There is one library, shared.

## Table of contents

1. [How expansion works](#1-how-expansion-works)
2. [First launch](#2-first-launch)
3. [The tray, and why the window closes to it](#3-the-tray-and-why-the-window-closes-to-it)
4. [Creating abbreviations](#4-creating-abbreviations)
5. [Per-abbreviation settings](#5-per-abbreviation-settings)
6. [Variables](#6-variables)
6a. [Fields: expansions that ask you something](#6a-fields-expansions-that-ask-you-something)
7. [Case follows your typing](#7-case-follows-your-typing)
8. [Categories](#8-categories)
9. [Quick Insert, and expanding on demand](#9-quick-insert-and-expanding-on-demand)
10. [Sharing one library with QUILL](#10-sharing-one-library-with-quill)
10a. [Where it works](#10a-where-it-works)
10b. [Inside QUILL itself](#10b-inside-quill-itself)
11. [Where expansion refuses to run](#11-where-expansion-refuses-to-run)
12. [Typing versus pasting](#12-typing-versus-pasting)
13. [Import and export](#13-import-and-export)
14. [Settings reference](#14-settings-reference)
15. [Keyboard reference](#15-keyboard-reference)
16. [Portable mode](#16-portable-mode)
17. [Safe Mode](#17-safe-mode)
18. [Privacy](#18-privacy)
19. [Troubleshooting](#19-troubleshooting)

## 1. How expansion works

While Inkwell is running it watches for typing so that it can recognise the end
of a word. It keeps a short rolling window of recent characters -- at most 64 --
and nothing else.

When you type a character that ends a word (a space, Enter, Tab, or one of
`. , ; : ! ? ) ] } " '`), Inkwell checks the word you just finished against your
abbreviations. If one matches, and that entry accepts the character you typed,
Inkwell:

1. Sends backspaces to erase the abbreviation.
2. Types the expansion.
3. Moves the caret, if the expansion contains a `${cursor}` marker.
4. Speaks or plays a sound, if that entry asks for it.

The character you typed stays where it is. `btw ` keeps the space; `btw.` keeps
the full stop.

Nothing goes near the clipboard during an ordinary expansion.

## 2. First launch

Inkwell opens its window, shows the abbreviations you already have -- including
everything QUILL knows about -- and starts watching for typing. A handful of
common shorthand entries (`btw`, `imo`, `asap`, and so on) come built in so
there is something to try immediately.

If Windows refuses the keyboard hook, Inkwell says so in a dialog rather than
sitting there looking like it works. See [Troubleshooting](#19-troubleshooting).

## 3. The tray, and why the window closes to it

Expansion is a background service. Closing the window keeps it running and tucks
Inkwell into the notification area; the tray icon's menu reopens it, offers Quick
Insert, and can turn expansion off.

**What to look for.** Quill Inkwell's icon is a gold nib dipped into a white
inkwell, on a terracotta-orange tile. If you have used an earlier build, this is
new: Inkwell used to share Quill Radio's blue broadcast-wave icon, so on a
desktop with more than one QuillVille app installed several of them looked
identical. Every app in the family now has its own: they all share the same
rounded tile shape and the same gold accent, but each has its own colour and its
own picture.

Turn off **Options > Close button keeps expanding** if you would rather the close
button really exit. **Options > Start Quill Inkwell with Windows** starts it
hidden at login, which is how most people run it.

## 4. Creating abbreviations

**Abbreviations > Manage Abbreviations...** (Ctrl+M) is the full list: search it,
filter it by category, and add, edit, enable, disable, or delete entries.

**Abbreviations > New from Clipboard...** (Ctrl+Shift+N) is the fast path. Copy
a block of text anywhere, press Ctrl+Shift+N, and Inkwell opens a new entry with
that text already filled in as the expansion -- you only supply the trigger.

An abbreviation can be anything you can type without a space: `addr`, `sig`,
`@@`, `;;date`. Longer abbreviations always win over shorter ones, so `addr`
cannot be swallowed by `ad`.

## 5. Per-abbreviation settings

Every entry decides these for itself, in the edit dialog:

| Setting | What it does |
| --- | --- |
| Enabled | Off keeps the entry without expanding it. |
| Case sensitive | On means only the exact spelling matches. |
| Category | Free text; groups the list and Quick Insert. |
| Expand after | A space or punctuation, a space only, punctuation only, or never. |
| Speak | Nothing, the abbreviation, or the expanded text. |
| Sound | Follow the global setting, always play, or never play. |
| Add a trailing space after punctuation | Adds one space after the punctuation that fired it. |

Two of these are worth explaining properly.

**Expand after = Never** means the entry never fires on its own; it is reachable
only from Quick Insert. That is the right home for a long expansion, or for one
you would not want appearing by accident.

**Add a trailing space after punctuation** only applies to punctuation triggers,
because a space trigger already leaves a space and doubling it reads badly. With
it on, `co.` becomes `Company, ` rather than `Company ,`.

## 6. Variables

Anywhere in an expansion:

| Variable | Becomes |
| --- | --- |
| `${date}` | The date, long form (June 15, 2026) |
| `${time}` | The time (2:45 PM) |
| `${datetime}` | Both |
| `${day}` | Day of the month |
| `${month}` | Month name |
| `${year}` | Four-digit year |
| `${username}` | Your Windows user name |
| `${clipboard}` | Whatever text is on the clipboard right now |
| `${cursor}` | Nothing -- but the caret lands here afterwards |

`${clipboard}` is read at the moment the expansion fires and is never stored.

## 6a. Fields: expansions that ask you something

A signature is the same every time. A letter opening, a bug report, a booking
confirmation is not -- it is the same except for a name, a date, a reference. Put
a field in the expansion and Inkwell asks for it before typing:

```
Dear ${field:Name},

Thank you for your message about ${field:Subject}. I will reply by
${field:Reply by=the end of the week}.

Kind regards to ${field:Name}.
```

- `${field:Label}` asks for a value with that label.
- `${field:Label=something}` offers a starting value you can accept or replace.
- The **same label used twice is asked once** and filled everywhere, so the name
  in the greeting also lands in the sign-off.

A small form appears with one labelled box per field, in the order the template
asks for them. Tab moves between them, Enter moves to the next one, Enter on the
last accepts, and Escape cancels -- and cancelling leaves whatever you typed
exactly as it was, because nothing is erased until you accept.

`${cursor}` still works alongside fields: the caret lands where the template put
it, after the answers are in.

## 7. Case follows your typing

For an entry that is not case sensitive, the case you type carries over:

- `btw` gives the expansion exactly as you wrote it.
- `Btw` capitalises each word.
- `BTW` shouts the whole thing.

## 8. Categories

A category is free text -- Work, Personal, Email, Forms, whatever suits. The
manager's category filter narrows the list to one at a time, and entries with no
category are listed under Uncategorised. Nothing about a category changes how an
entry expands; it exists to keep a long list navigable.

## 9. Quick Insert, and expanding on demand

**Ctrl+K** in the window, or **Ctrl+Alt+Shift+K** from anywhere, opens a
type-to-filter picker over every enabled abbreviation, ordered with the ones you
use most at the top. Type a few letters, arrow down, press Enter, and the
expansion is typed into whatever window you were working in.

Quick Insert is the only way to reach an entry whose trigger mode is Never, and
the easiest way to use an abbreviation you have not memorised yet.

**Expand the word I just typed** -- **Ctrl+Alt+Shift+X** from anywhere, or the
Abbreviations menu -- expands the word before the cursor without waiting for a
space or punctuation. Use it mid-word, at the end of a line where you do not want
a trailing space, or for an abbreviation you have set never to expand on its own.

**Taking one back.** If an abbreviation expands when you did not want it, press
**Backspace immediately afterwards** and Inkwell puts your original abbreviation
back. The offer lasts a few seconds and only in the window where it expanded --
after that, or after any other keystroke, Backspace does what it always does.

## 10. Sharing one library with QUILL

Inkwell and QUILL use the same `abbreviations.json` in the same data folder. Add
an abbreviation in QUILL's own Abbreviation Manager and it expands system-wide
within moments; add one here and QUILL's editor knows it. Inkwell re-reads the
file whenever it changes on disk, so neither app needs restarting.

This is also why an installed Inkwell keeps its data in `%APPDATA%\Quill` rather
than a folder of its own.

## 10a. Where it works

Expansion runs wherever you can type or edit: browsers, mail, chat, forms,
office applications, code editors, terminals, and dialog boxes. Two limits are
worth knowing about, because both look like faults and neither is one.

**Somewhere you cannot type.** Before replacing anything, Inkwell checks that
the thing with focus actually accepts text. Typing into a list that is doing
type-ahead, or a page where Backspace means "go back", would be worse than not
expanding at all. Where it cannot tell, it goes ahead -- a missed expansion is
the more annoying failure.

**An application running as administrator.** Windows does not let a normal
program see keys typed into an elevated one, so nothing expands there. Inkwell
says so the first time focus lands in such a window. If you need expansion in
it, start Inkwell as administrator too.

## 10b. Inside QUILL itself

QUILL expands your abbreviations in its own editor, from the document, without
synthesising a single keystroke -- which is faster and safer than anything a
system-wide expander can do. So Inkwell deliberately keeps out of QUILL's editor
window and lets it do the work. Same abbreviations, same settings, same results;
only the mechanism differs, and you should never be able to tell.

## 11. Where expansion refuses to run

Typing into the wrong window is worse than not expanding at all, so Inkwell
refuses outright in:

- Password managers (1Password, Bitwarden, KeePass and KeePassXC, LastPass,
  Dashlane, Keeper, NordPass, RoboForm, Enpass).
- The Windows sign-in and lock screens, the credential prompt, and the UAC
  dialog.
- Any window whose title suggests a credential prompt -- sign in, log on,
  password, passcode, authenticate, unlock, Windows Security.

**Options > Excluded Applications...** adds your own, one program file name per
line (`notepad.exe`). The decision is made from the foreground window alone --
its program, its class, and its title. Nothing is ever decided from what you
typed.

## 12. Typing versus pasting

By default an expansion is typed, as synthesised keystrokes. That is the right
default: it never touches your clipboard.

A few applications -- some rich editors, some terminals -- drop fast synthetic
keystrokes. For those, turn on **Options > Insert by pasting**. Inkwell then puts
the expansion on the clipboard, pastes it, and puts your previous clipboard
contents back. It is a fallback precisely because borrowing the clipboard is
rude, and it always restores.

This can also be set **per application**, which is usually what you want: one
stubborn program should not mean every other program has its clipboard borrowed.
List the program's file name under `paste_processes` in `inkwell.json` beside the
abbreviation library, and only that program uses the clipboard route.

## 13. Import and export

The manager's **Import...** and **Export...** buttons read and write the shared
library as JSON. Export is the honest backup of everything, including every
per-entry setting; import merges entries in.

## 14. Settings reference

Inkwell's own preferences live in `inkwell.json` beside the library:

| Setting | Default | Meaning |
| --- | --- | --- |
| Expand in other applications | On | The master switch (Ctrl+Shift+E). |
| Insert by pasting | Off | Use the clipboard route (section 12). |
| Announce every expansion | Off | A spoken confirmation on top of per-entry speech. |
| Excluded applications | Empty | Your additions to the permanent list. |
| Start with Windows | Off | Starts hidden in the tray at login. |
| Start minimized to the tray | Off | Opens hidden. |
| Close button keeps expanding | On | Close hides to the tray instead of exiting. |

Abbreviations themselves are not listed here: they are shared, and they live in
QUILL's `abbreviations.json`.

## 15. Keyboard reference

| Action | Keys |
| --- | --- |
| Show or hide Inkwell | Ctrl+Alt+Shift+I |
| Quick Insert from anywhere | Ctrl+Alt+Shift+K |
| Expand the word I just typed | Ctrl+Alt+Shift+X |
| Take back the expansion that just fired | Backspace, immediately |
| Manage abbreviations | Ctrl+M |
| Quick Insert | Ctrl+K |
| New abbreviation from the clipboard | Ctrl+Shift+N |
| Turn expansion on or off | Ctrl+Shift+E |
| Minimize to the tray | Ctrl+W |

Every dialog follows QUILL's dialog conventions: Escape cancels, Enter activates
the default button, every control has a name your screen reader announces, and
focus starts where the work does.

## 16. Portable mode

The portable zip carries a `data` folder next to `QuillInkwell.exe`. When that
folder is present, the abbreviation library and settings live on the stick, and a
portable QUILL sitting beside it shares them. Remove the stick and nothing is
left behind on the machine.

## 17. Safe Mode

With `QUILL_SAFE_MODE=1` set, Inkwell starts without installing the keyboard
hook at all and says so. The manager still works, so you can edit abbreviations;
nothing is watched and nothing is typed.

## 18. Privacy

Inkwell has to notice typing to recognise an abbreviation. Here is exactly what
that means:

- **Bounded.** At most 64 characters are held at once, in memory only.
- **Never stored.** Nothing is written to disk, added to a log, or sent
  anywhere. There is no network code in the expansion path.
- **Cleared constantly.** The buffer empties after every expansion, on Escape,
  on any arrow key, Home, End, Page Up or Down, Insert, Delete, or function key,
  on any Ctrl or Alt combination, whenever focus moves to another window, and
  whenever expansion is paused.
- **Content-blind.** No rule anywhere looks at what you typed to decide whether
  to keep it. The check that suppresses expansion looks only at which window has
  focus, which is why it cannot be fooled by an unusual password field.
- **Its own output is ignored.** Inkwell marks the keystrokes it synthesises and
  skips them, so an expansion can never feed itself. Keystrokes from dictation
  software and on-screen keyboards are *not* skipped -- those users get
  expansion like everyone else.
- **Switchable.** Ctrl+Shift+E stops it, the tray menu stops it, and Safe Mode
  never starts it.
- **Self-repairing, not self-extending.** Windows silently removes a keyboard
  hook that responds too slowly, so Inkwell quietly re-installs its own every few
  minutes. That refresh changes nothing about what is watched or kept.

## 19. Troubleshooting

**Nothing expands anywhere.** Check Ctrl+Shift+E is on, and that the window in
front is not one of the excluded ones (section 11). If Inkwell warned at startup
that Windows refused the keyboard hook, see the next item.

**Nothing expands in one particular application.** If Inkwell announced that the
application runs as administrator, that is the reason (section 10a). Otherwise the
application may not report itself as editable, or may be dropping the typed
keystrokes -- press Ctrl+Alt+Shift+X there to expand on demand, and if that works
but ordinary typing does not, add the program to the per-application paste list
(section 12).

**"Expansion unavailable" at startup.** Windows refused the low-level keyboard
hook. Almost always this means the application you are typing into runs at a
higher privilege level than Inkwell -- Windows does not let a normal program see
keys sent to an elevated one. Start Inkwell the same way you start that
application.

**It expands in QUILL but not elsewhere, or the reverse.** They share a library
but not a switch: QUILL's editor expansion has its own setting, and Inkwell's
Ctrl+Shift+E governs everywhere else.

**A new abbreviation is not recognised.** Both apps re-read the file when it
changes; if one was mid-edit when the other saved, close the manager and try
again.

**Some text arrives scrambled or truncated in one particular app.** Turn on
Options > Insert by pasting (section 12).

**An abbreviation fires when I do not want it.** Set that entry's *Expand after*
to Never; Quick Insert can still reach it.
