# QUILL Lite -- sign-off checklist

One pass, top to bottom, ticking boxes. Every step says exactly what to press,
exactly what to type, and the one thing that decides pass or fail.

The narrative version of every feature below is
[the user guide](../../standalone/quilllite/docs/userguide.md); the reasoning is
in [the PRD](../../standalone/quilllite/docs/prd.md) and
[the release notes](../../standalone/quilllite/docs/release-notes-1.0.md).

**Why this file exists.** Everything an automated test can answer about
QUILL Lite is already answered: the wx-free core suites (`tests/unit/core/lite`,
204 tests), the behavioural coverage gate over every handler in its command
table (198 today, none of them shape-only), the F1 audit, the access-key and over-announce gates, the family gates
that hold it and QUILL to the same keys and the same words, and 21 live checks
against a real `RICHEDIT50W` (`standalone/quilllite/tests/probe_live.py`). What
none of them can answer is what a person actually *hears*. That is this list.

Counts in that paragraph are the kind of thing that rots; `python -m
quill.tools.platform_report` is the answer that is true today.

## Before you start (3 minutes)

- Install or launch the build under test. Note the version from
  **Help > About QUILL Lite**: `____________`
- Have a screen reader running and speaking (JAWS or NVDA). Note which, and its
  version: `____________`
- QUILL Lite keeps everything in `%LOCALAPPDATA%\QuillLite`, separate from
  QUILL's `%APPDATA%\Quill`. For a clean run, rename that folder first; to keep
  your real one, take a copy.
- **Fail means:** it did not happen, or it happened silently, or what you heard
  differs from what this file quotes. Write down what you actually heard --
  "nothing" and "the wrong thing" are different bugs.
- Have three files to hand: a `.txt` saved with Windows line endings, a `.txt`
  saved with Unix line endings (any file from a git checkout will do), and any
  `.rtf`.

## The 15-minute pass

No time for the whole thing? Run exactly these seventeen and stop:
**L-02, L-05, L-09, L-14, L-21, L-30, L-38, L-46, L-54, L-61, L-90, L-105,
L-121, L-157, L-160, L-226, L-241.**

They cover the four things most likely to be wrong and worst if they are: the
document announces itself, F1 answers, the status bar is reachable, and a file
comes back byte-for-byte. L-90 is there because a status cell that misreports
what typing is about to do is the one defect this product cannot ship, and it
was shipped once already. **L-105** joined it on 2026-09-10 for the same reason
in reverse: a status bar that reads its own text back truncated is a cell
quietly lying about a fact, and the only place it shows is a narrow window on
the machine it was reported from.

Three more joined on 2026-09-15, and all three are regressions somebody
reported rather than risks somebody imagined. **L-121**: the Format cell did not
change when the document did, which is the one place anybody checks what kind of
document they are in. **L-157**: Ctrl+Home onto a heading announced nothing,
because a cue queued behind the screen reader is cancelled outright on a big
jump. **L-160** is the counterweight -- everything added in Block Q is speech,
and over-announcing is absorbed as "this app is chatty" and never filed, which
is exactly why it needs a box to tick.

**L-226** joined on 2026-09-18, and it is the same defect as L-90 one more time:
the Encoding and Line Endings cells read "UTF-8" and "CRLF" in a rich text
document, which has neither. A cell stating a fact the document does not have is
the one thing this status bar must never do.

**L-241** joined on 2026-09-19 and is the only test in the short run about
something *not* happening: the session window's Forget must never touch a file.
Forgetting is safe by design and by test, and the one way that could become untrue
is a change nobody checked -- so it is checked on every pass, by hand, in the
folder.

---

## Block A -- Opening, and where focus lands (5 min)

**L-01. The window announces itself as a document**
- Do: launch QUILL Lite with nothing open.
- Pass: you hear a window title containing **"1: Untitled - QUILL Lite (plain
  text)"**. The number leads.
- [ ] pass  [ ] fail: ______

**L-02. Focus starts in the document**
- Do: launch QUILL Lite, do not touch anything, type `hello`.
- Pass: the letters go into the document. You did not have to Tab first, and
  the reader announced the edit control, not a button.
- [ ] pass  [ ] fail: ______

**L-03. Typing is not narrated twice**
- Do: type a sentence at normal speed.
- Pass: you hear your own characters or words, exactly as your reader is
  configured to echo them -- and **nothing else**. No status chatter per
  keystroke.
- [ ] pass  [ ] fail: ______

**L-04. Opening a second document numbers it**
- Do: press **Ctrl+N**.
- Pass: the title is **"2: Untitled - ..."**. The first document is still open.
- [ ] pass  [ ] fail: ______

**L-05. Alt+Tab shows QUILL Lite once, and the Window menu shows both**
- Do: press **Alt+Tab**, then come back. Open the **Window** menu (Alt+W).
- Pass: Alt+Tab lists QUILL Lite **once** (this is expected -- documents are
  inside one window). The Window menu lists **1** and **2**, each with its
  Alt+digit, and a mark on the one you are in.
- [ ] pass  [ ] fail: ______
- Note: if this surprises you, that is the trade the numbering buys, and it is
  written up in the user guide under "Documents are numbered". Say so if it
  feels wrong in use -- that is the feedback worth having.

**L-06. Alt+2 goes straight to document 2**
- Do: from document 1, press **Alt+2**.
- Pass: focus is in document 2 and the reader announces its title.
- [ ] pass  [ ] fail: ______

**L-07. Ctrl+F6 and Ctrl+Tab both move**
- Do: press **Ctrl+F6**. Then **Ctrl+Tab**. Then **Ctrl+Shift+Tab**.
- Pass: each moves you to another document and announces it. Both keys work --
  neither is dead.
- [ ] pass  [ ] fail: ______

**L-08. Closing a document does not renumber the others**
- Do: with 1, 2 and 3 open, close document 2 (**Ctrl+W** in it).
- Pass: the Window menu still shows **1** and **3**. Document 3 did not become
  document 2.
- [ ] pass  [ ] fail: ______

---

## Block B -- F1, everywhere (5 min)

**L-09. F1 in the document says what the document is for**
- Do: put the cursor in the text and press **F1**.
- Pass: a help window opens, focus is in a text field you can arrow through,
  and it says both what *this window* is for and what the *document control*
  does -- including that F6 reaches the status bar. **Escape** returns you to
  the text.
- [ ] pass  [ ] fail: ______

**L-10. F1 answers differently in the two modes**
- Do: press **Alt+Shift+F** to switch to rich text (answer **Yes** if asked),
  then **F1** in the document.
- Pass: the answer now mentions bold, headings and Describe Formatting. It is
  not the plain-text answer.
- [ ] pass  [ ] fail: ______

**L-11. F1 on a control in a dialog**
- Do: **Ctrl+F** to open Find. Tab to **Match case**. Press **F1**.
- Pass: you hear what the Find window is for *and* what that checkbox does.
- [ ] pass  [ ] fail: ______

**L-12. Every field in Preferences has a name**
- Do: **Ctrl+,** then Tab through every control.
- Pass: each one announces a **name** -- "New documents are", "Theme",
  "Copy unsaved work aside every, seconds", "Editor font" -- not just
  "combo box" or "edit".
- [ ] pass  [ ] fail: ______
- This is the one that was broken in an early build. If any control announces
  only its type, that is a fail even if you can guess what it is.

**L-13. Leaving Preferences says it once, or not at all**
- Do: from Preferences, press **Escape**. Then open it again and press
  **Enter**.
- Pass: on Escape you hear the document window again and **no** "exited
  Preferences dialog". On Enter you hear **"Preferences saved"** once.
- [ ] pass  [ ] fail: ______

---

## Block C -- The status bar (5 min)

**L-14. F6 lands in the status bar and names the region**
- Do: from the document, press **F6**.
- Pass: you hear **"Status bar,"** followed by a cell and its value.
- [ ] pass  [ ] fail: ______

**L-15. Arrows move between cells, and each announces itself**
- Do: press **Right** several times, then **Left**.
- Pass: each cell announces its name and its value -- Position, Word Count,
  Character Count, Selection, Typing Mode, Tab Mode, Format, Heading, Encoding,
  Line Endings, Saved State. The region name is **not** repeated on every one.
- [ ] pass  [ ] fail: ______

**L-16. Home and End jump to the ends of the row**
- Do: press **Home**, then **End**.
- Pass: first cell, then last cell.
- [ ] pass  [ ] fail: ______

**L-17. Escape returns to the document**
- Do: press **Escape**.
- Pass: focus is back in the text, at the cursor you left.
- [ ] pass  [ ] fail: ______

**L-18. Enter on Position goes to a line**
- Do: **F6**, arrow to **Position**, press **Enter**.
- Pass: the Go to line window opens with the field focused and its number
  selected.
- [ ] pass  [ ] fail: ______

**L-19. The counts are right**
- Do: type exactly `one two three` in an empty document. **F6**, arrow to Word
  Count.
- Pass: **3 words**. Characters says **13**.
- [ ] pass  [ ] fail: ______

**L-20. The message cell brings back what was said**
- Do: press **Ctrl+S** and save somewhere. Then **F6** and read the first cell.
- Pass: it still says **"Saved <filename>"**.
- [ ] pass  [ ] fail: ______

---

## Block D -- Files come back unchanged (6 min)

This block is the product. Take it slowly.

**L-21. A Windows file stays a Windows file**
- Do: open your CRLF `.txt`. **F6**, read **Line Endings**. **Escape**,
  **Ctrl+S**, close, reopen.
- Pass: Line Endings says **CRLF (Windows)** both times, and the file's size on
  disk is unchanged.
- [ ] pass  [ ] fail: ______

**L-22. A Unix file stays a Unix file**
- Do: the same with your LF `.txt`.
- Pass: **LF (Unix...)** both times, size unchanged. This is the one that
  matters -- an editor that silently adds carriage returns will show up in
  somebody's version control diff as "changed every line".
- [ ] pass  [ ] fail: ______

**L-23. Encoding is reported and kept**
- Do: **F6**, read **Encoding** on a file you know is UTF-8.
- Pass: **UTF-8**, or **UTF-8 with BOM** if it has one. Not "Windows-1252".
- [ ] pass  [ ] fail: ______

**L-24. Changing the line endings on purpose works**
- Do: **Ctrl+Alt+E**. Tab to **Line endings**, choose the other one, **Enter**.
  Then **Ctrl+S**.
- Pass: you hear the change announced, the status bar cell updates, and the
  saved file really has the other line endings (check in another editor or with
  `file`).
- [ ] pass  [ ] fail: ______

**L-25. Enter on the Encoding cell opens the same window**
- Do: **F6**, arrow to **Encoding**, **Enter**.
- Pass: the File format window opens.
- [ ] pass  [ ] fail: ______

**L-26. A file that does not end in a newline does not grow one**
- Do: open a file whose last line has no newline. Save it. Check the size.
- Pass: unchanged.
- [ ] pass  [ ] fail: ______

---

## Block E -- Rich text and headings (8 min)

**L-27. Switching to rich text warns first**
- Do: in a plain document with text in it, press **Alt+Shift+F** twice (to
  rich, then back to plain).
- Pass: going *to plain* asks "Switching to plain text removes all formatting.
  Continue?" and the default button is **No** -- pressing Enter does **not**
  discard the formatting.
- [ ] pass  [ ] fail: ______

**L-28. Bold announces its new state**
- Do: in rich text, select a word and press **Ctrl+B**, then **Ctrl+B** again.
- Pass: **"Bold on"** then **"Bold off"**. Not "Bold" both times.
- [ ] pass  [ ] fail: ______

**L-29. A heading is a heading**
- Do: type `Chapter One`, press **Ctrl+Alt+1**.
- Pass: you hear **"Heading 1"**.
- [ ] pass  [ ] fail: ______

**L-30. Describe Formatting reports the heading, standing at its start**
- Do: press **Home** to go to the very start of that heading line, then
  **Ctrl+Shift+D**.
- Pass: you hear something like **"Arial, 20 point, heading 1, bold"**. It does
  **not** describe the paragraph above.
- [ ] pass  [ ] fail: ______
- This is the second bug PR #1490 found. If it describes the line above, the
  fix has regressed.

**L-31. Headings can be navigated**
- Do: add a second heading further down (**Ctrl+Alt+2**). From the top, press
  **Ctrl+Alt+H**.
- Pass: the cursor moves and you hear **"Heading 2: <the heading's text>"** --
  the level *and* the words.
- [ ] pass  [ ] fail: ______

**L-32. The headings list works from the keyboard**
- Do: **Ctrl+Alt+L**.
- Pass: a list opens with both headings, focus is in the list, **Enter** goes
  to the chosen one, **Escape** cancels.
- [ ] pass  [ ] fail: ______

**L-33. A saved RTF reads as headings in Word**
- Do: save as `.rtf`. Open it in Word or WordPad.
- Pass: the headings are visibly bold and larger. (They are presentational, not
  Word styles -- Word's navigation pane may not list them. That is expected and
  is in the PRD.)
- [ ] pass  [ ] fail: ______

**L-34. Bullets, justify and line spacing**
- Do: **Ctrl+Shift+L**, then **Ctrl+J**, then **Ctrl+2**.
- Pass: each announces its outcome ("Bullets on", "Justified", "Double
  spacing") and each visibly changes the paragraph.
- [ ] pass  [ ] fail: ______

**L-35. Grow and shrink step sensibly**
- Do: select a word, press **Ctrl+Shift+>** three times, then
  **Ctrl+Shift+<** three times.
- Pass: each press announces a point size, and the sizes are round numbers
  (12, 14, 16...), not 11.5 or 13.
- [ ] pass  [ ] fail: ______

**L-36. Dark mode never reaches the file**
- Do: with **Dark Mode** on (View menu), save an `.rtf`, then open it in
  WordPad.
- Pass: the text in WordPad is **black on white**, not light grey. If it is
  grey, the theme leaked into the document.
- [ ] pass  [ ] fail: ______

---

## Block F -- Selection, bookmarks, characters (6 min)

**L-37. Select word, line, paragraph**
- Do: put the cursor mid-word. **Ctrl+Shift+W**, then **Ctrl+Shift+E**, then
  **Ctrl+Shift+H**.
- Pass: each selects the right thing and announces **what** it took and how
  many characters ("Selected word, 5 characters").
- [ ] pass  [ ] fail: ______

**L-38. Expand grows outwards**
- Do: press **Ctrl+Shift+X** four times in a row.
- Pass: the selection grows each time and the scope is named each time -- word,
  line, sentence, paragraph... When it reaches the whole document it says so
  rather than going silent.
- [ ] pass  [ ] fail: ______

**L-39. A bookmark can be set and returned to**
- Do: partway down a long document press **Ctrl+Shift+B**. Move to the top
  (**Ctrl+Home**). Press **F2**.
- Pass: setting says **"Bookmark 1 set: <the line's text>"**; F2 takes you back
  and says the same.
- [ ] pass  [ ] fail: ______

**L-40. Bookmarks move with the text**
- Do: with that bookmark set, go to the very top and type three lines of new
  text. Press **F2**.
- Pass: you land on the **same line of text** as before, not three lines above
  it.
- [ ] pass  [ ] fail: ______

**L-41. The bookmark list can remove as well as go**
- Do: **Alt+Shift+G**. Arrow to a bookmark. Tab to **Remove**, press it.
- Pass: it is removed, you hear so, and the document is unchanged.
- [ ] pass  [ ] fail: ______

**L-42. Describe Character identifies an invisible**
- Do: type a normal space, put the cursor on it, press **Ctrl+Shift+C**. Then
  do the same on a letter.
- Pass: the space is named ("Space, U+0020..."), the letter is named. They are
  different answers.
- [ ] pass  [ ] fail: ______

---

## Block G -- Find, replace, tools (5 min)

**L-43. Find wraps and says so**
- Do: in a document with one occurrence of a word, put the cursor after it and
  press **Ctrl+F**, type the word, **Enter**.
- Pass: it finds it **and** says **"Wrapped to the start"**. Without that, one
  match sounds identical to none.
- [ ] pass  [ ] fail: ______

**L-44. F3 keeps working after the Find window closes**
- Do: **Escape** out of Find, then press **F3** twice.
- Pass: it keeps moving between matches.
- [ ] pass  [ ] fail: ______

**L-45. Replace All counts**
- Do: **Ctrl+H**, replace a common word, press **Replace all**.
- Pass: you hear **"Replaced N occurrences"** with a real number.
- [ ] pass  [ ] fail: ______

**L-46. Sorting is one undo step**
- Do: in a plain document with five unsorted lines, press **Ctrl+Alt+S**, then
  **Ctrl+Z** once.
- Pass: sorting announces how many lines; **one** Ctrl+Z puts them all back.
- [ ] pass  [ ] fail: ______

**L-47. Case conversion works on a selection**
- Do: select a sentence, press **Ctrl+Shift+U**, then **Ctrl+Z**, then
  **Ctrl+Shift+G**.
- Pass: uppercase, undone, then Title Case -- and Title Case does **not** turn
  `don't` into `Don'T`.
- [ ] pass  [ ] fail: ______

---

## Block H -- The clipboard (4 min)

**L-48. Paste Text Only strips formatting**
- Do: copy some formatted text from a web page or Word. In a **rich text**
  QUILL Lite document press **Ctrl+V**, then undo, then **Ctrl+Shift+V**.
- Pass: Ctrl+V brings the formatting; Ctrl+Shift+V brings the words only, and
  says how many characters.
- [ ] pass  [ ] fail: ______

**L-49. The copy tray remembers across a restart**
- Do: select text, **Ctrl+Alt+Y**. Close QUILL Lite entirely. Reopen. Press
  **Ctrl+Alt+V**.
- Pass: the slot is still there, with a readable preview, and pastes.
- [ ] pass  [ ] fail: ______

**L-50. The collector gathers**
- Do: **Ctrl+Alt+G** on three different selections, then **Ctrl+Alt+Shift+G**.
- Pass: each collect says how many pieces; the paste brings all three, in the
  order collected, with a divider between.
- [ ] pass  [ ] fail: ______

**L-51. The clip library fills by itself**
- Do: **Ctrl+Alt+Shift+M**.
- Pass: things you copied earlier are listed, newest first, and one can be
  pasted with **Enter**.
- [ ] pass  [ ] fail: ______

---

## Block I -- Recovery and sessions (6 min, includes a deliberate kill)

**L-52. Unsaved work survives a kill**
- Do: type several paragraphs into a new document. Do **not** save. Wait 40
  seconds (the copy is taken every thirty seconds, as QUILL's is). Kill
  QUILL Lite from Task Manager.
  Reopen it.
- Pass: the text is back, in its own window, marked unsaved, and you hear
  **"Recovered unsaved work from the last session"**.
- [ ] pass  [ ] fail: ______

**L-53. Saving clears the recovery copy**
- Do: save that recovered document, close QUILL Lite normally, reopen.
- Pass: nothing is offered back. `%LOCALAPPDATA%\QuillLite\recovery` is empty.
- [ ] pass  [ ] fail: ______

**L-54. Last session's documents reopen**
- Do: open two saved files. Close QUILL Lite with **Ctrl+Q**. Reopen.
- Pass: both are back, numbered in the same order.
- [ ] pass  [ ] fail: ______

**L-55. Naming a file on the command line wins over the session**
- Do: close QUILL Lite. Open a `.txt` from Explorer.
- Pass: that file opens, and last session's documents do **not** bury it.
- [ ] pass  [ ] fail: ______

**L-56. Exit asks about each unsaved document and one Cancel stops the lot**
- Do: with two modified documents, press **Ctrl+Q** and **Cancel** the first
  prompt.
- Pass: nothing closes. Both documents are still there.
- [ ] pass  [ ] fail: ______

---

## Block J -- Turning things off (4 min)

**L-57. Unchecking rich text removes the whole Format menu**
- Do: **View > Customize Features**, uncheck **Rich text and the Format menu**,
  Save.
- Pass: the Format menu is gone from the bar, and **Ctrl+B** now does nothing
  (rather than doing something invisible).
- [ ] pass  [ ] fail: ______

**L-58. And it comes back**
- Do: check it again, Save.
- Pass: the Format menu returns and Ctrl+B works.
- [ ] pass  [ ] fail: ______

**L-59. Three things start switched off, and are findable**
- Do: open **Customize Features** on a fresh profile.
- Pass: **Autocorrect while typing**, **Timestamped backups** and **Go To
  Anything** are unchecked, each with a sentence saying why. Every checkbox
  announces its name and state.
- [ ] pass  [ ] fail: ______

**L-60. Autocorrect, once switched on, actually corrects**
- Do: switch on **Autocorrect while typing**, Save, then type `"quoted"` and
  `a--b`.
- Pass: curly quotes and an em dash.
- [ ] pass  [ ] fail: ______

---

## Block K -- Printing and the palette (4 min)

**L-61. Ctrl+P reaches a printer**
- Do: **Ctrl+P**.
- Pass: the Windows print dialog opens and is fully keyboard-navigable.
  Cancelling says nothing (cancelling is not a failure). Printing says
  **"Printing <filename>"**.
- [ ] pass  [ ] fail: ______

**L-62. What comes out of the printer**
- Do: print a two-page plain document.
- Pass: the text is there, long lines are wrapped rather than cut off at the
  right edge, and each page has a footer with the filename and "Page N of M".
- [ ] pass  [ ] fail: ______
- Rich formatting is **expected** not to print in 1.0 -- headings come out
  marked `[H1]` rather than styled. That is documented, not a bug.

**L-63. Page Setup is shared and sticks**
- Do: **Ctrl+Alt+P**, change the paper size, OK. Open it again.
- Pass: it remembers, and so does a second document.
- [ ] pass  [ ] fail: ______

**L-64. The command palette finds a command by what it does**
- Do: **Ctrl+Shift+P**, type `sort`.
- Pass: the Sort Lines commands are listed **with their keys beside them**,
  each row announced as you arrow, and **Enter** runs the one you are on.
- [ ] pass  [ ] fail: ______

**L-65. Ctrl+F1 lists every key, and the list is readable**
- Do: **Ctrl+F1**.
- Pass: focus is in a text field you can arrow through line by line, every menu
  is there with its keys, and **Escape** closes it.
- [ ] pass  [ ] fail: ______

---

## Block L -- The things that must never happen (3 min)

**L-66. Nothing is announced twice**
- Do: use the app normally for two minutes -- save, format, search, switch
  documents.
- Pass: you never hear the same sentence twice in a row, and you never hear
  QUILL Lite repeat a window title or control name your reader has just said.
- [ ] pass  [ ] fail: ______

**L-67. No key advertises something that does not happen**
- Do: open each menu and read the keys shown. Try five at random.
- Pass: every key shown does what its item says.
- [ ] pass  [ ] fail: ______

**L-68. Alt+letter reaches what it claims**
- Do: in each menu, press each item's Alt letter.
- Pass: each **presses** the item. If a letter merely moves focus between two
  items, two items are claiming it -- record which menu.
- [ ] pass  [ ] fail: ______

**L-69. Escape never traps you**
- Do: open every dialog in turn (Find, Replace, Go to line, Headings,
  Bookmarks, File format, Preferences, Customize Features, the palette,
  Keyboard Shortcuts, About) and press **Escape** in each.
- Pass: every one closes and returns focus to the document.
- [ ] pass  [ ] fail: ______

**L-70. QUILL Lite does not create a QUILL data folder**
- Do: on a machine (or profile) with no QUILL installed, run QUILL Lite, save a
  file, quit.
- Pass: `%APPDATA%\Quill` does **not** exist. Only `%LOCALAPPDATA%\QuillLite`.
- [ ] pass  [ ] fail: ______

**L-71. Uninstalling leaves your work alone**
- Do: uninstall QUILL Lite.
- Pass: `%LOCALAPPDATA%\QuillLite` is still there, with settings and any
  recovery files.
- [ ] pass  [ ] fail: ______

---

## Block M -- Spelling, and where it stays quiet (6 min)

The last two steps are the ones this feature lives or dies by. A spell checker
that talks in a config file gets switched off permanently, and a checker that is
silently off cannot be told apart from a broken one.

**L-72. F7 reviews the document**
- Do: type `This sentance has a mispelled word.` and press **F7**.
- Pass: the Spelling Review opens on **sentance**, offers suggestions you can
  arrow through, and the count reads two.
- [ ] pass  [ ] fail: ______

**L-73. Changing a word actually changes the document**
- Do: choose the correct spelling and activate **Change**.
- Pass: the review moves to **mispelled**, and Escape leaves the corrected word
  in the document.
- [ ] pass  [ ] fail: ______

**L-74. Alt+Shift+F7 handles the single word**
- Do: put the cursor inside a misspelled word and press **Alt+Shift+F7**.
- Pass: a suggestions list opens named for the word, Enter replaces it, and you
  hear **"Replaced with ..."**.
- [ ] pass  [ ] fail: ______

**L-75. Ctrl+F7 selects the misspelling, not just the position**
- Do: from the top of the document, press **Ctrl+F7**.
- Pass: the reader reads the misspelled word because it is *selected*. Landing
  beside it silently is a fail -- there would be nothing to hear.
- [ ] pass  [ ] fail: ______

**L-76. Ctrl+Alt+F9 teaches a word, and says where it went**
- Do: on a misspelling, press **Ctrl+Alt+F9**, then **Ctrl+F7** from the top
  again. (**Alt+F7** is Word's key for *Next Misspelling* and is an alias for
  Ctrl+F7 here -- it does not teach anything.)
- Pass: you hear **"Added ... to your QUILL Lite dictionary"** -- naming *which*
  dictionary -- and the taught word is no longer found.
- [ ] pass  [ ] fail: ______

**L-77. A code file is quiet, and says so once**
- Do: open or save a file as **settings.json**, type `{ "mispelled": 1 }` and
  pause.
- Pass: on opening you hear once that spell check while typing is off for this
  file type. Typing produces **no** misspelling messages at all. Any alert here
  is a fail.
- [ ] pass  [ ] fail: ______

**L-78. F7 still works in that same file**
- Do: with the JSON still open, press **F7**.
- Pass: the review runs normally. F7 is never gated by the file type -- you
  asked for it.
- [ ] pass  [ ] fail: ______

**L-79. The toggle is per document**
- Do: with a `.txt` and the `.json` both open, press **Ctrl+Alt+F7** in the
  JSON, then switch to the text document (**Ctrl+F6**) and open the **Spelling**
  menu.
- Pass: the JSON now checks; the text document's **Check While Typing** mark is
  unchanged. One document's answer must not move the other's.
- [ ] pass  [ ] fail: ______

**L-80. A live misspelling does not interrupt your typing**
- Do: in a `.txt`, type a misspelled word and keep typing a full sentence.
- Pass: the misspelling appears in the **Message** cell (check with **F6**) and
  is **not** spoken over you. Speech here is a fail: you were mid-sentence.
- [ ] pass  [ ] fail: ______

---

## Block N -- Selecting (7 min)

Every step here is about what you *hear*. A selection you cannot confirm is a
selection you have to test by pressing something destructive.

**L-81. F8 extends as you move**
- Do: put the cursor mid-paragraph, press **F8**, then press Right six times and
  Down twice.
- Pass: you hear that selection started, and the selection grows as you move.
- [ ] pass  [ ] fail: ______

**L-82. Shift+F8 finishes and says how much**
- Do: press **Shift+F8**.
- Pass: you hear a character count **and** a word count. A silent finish is a
  fail -- the count is the only confirmation you get.
- [ ] pass  [ ] fail: ______

**L-83. Typing ends extend mode instead of extending**
- Do: press **F8**, move Right twice, then type a letter.
- Pass: the letter goes in and extend mode ends. It must not keep extending
  while you type.
- [ ] pass  [ ] fail: ______

**L-84. Ctrl+Shift+F8 gives a lost selection back**
- Do: select a paragraph (**Ctrl+Shift+H**), press Right to lose it, then press
  **Ctrl+Shift+F8**.
- Pass: the paragraph is selected again, and you hear the size.
- [ ] pass  [ ] fail: ______

**L-85. Expand and shrink walk both ways**
- Do: put the cursor in a word. Press **Ctrl+Shift+X** four times, then
  **Ctrl+Alt+Shift+X** four times.
- Pass: each press names the scope it took -- word, line, sentence, paragraph --
  and shrinking walks back down. Shrink must **not** say "nothing to shrink"
  while something is plainly selected.
- [ ] pass  [ ] fail: ______

**L-86. Shrink works on a selection you did not expand into**
- Do: press **Ctrl+Shift+H** to select the paragraph outright, then
  **Ctrl+Alt+Shift+X**.
- Pass: it shrinks to something smaller and names it. This is the case the old
  behaviour could not answer.
- [ ] pass  [ ] fail: ______

**L-87. Marks are not bookmarks**
- Do: press **Ctrl+Alt+Shift+K**, move to another line, press **Ctrl+M**.
- Pass: setting says which line and how many marks -- **"1 mark"**, not
  "1 marks" -- and Ctrl+M returns you there.
- [ ] pass  [ ] fail: ______

**L-88. Say Selection reads back, and summarises when long**
- Do: select a short phrase and press **Ctrl+Shift+Y**. Then select several
  paragraphs and press it again.
- Pass: the short one is read out in full; the long one is summarised with a
  count and its beginning and end, not read out entirely.
- [ ] pass  [ ] fail: ______

**L-89. Turning the Select menu off leaves Select All alone**
- Do: **View > Customize Features**, uncheck **The Select menu**, then check the
  Edit menu and press **Ctrl+A**.
- Pass: the Select menu is gone, F8 does nothing, and **Ctrl+A still selects
  everything**. Losing Select All here is a fail.
- [ ] pass  [ ] fail: ______

---

## Block O -- The 2026-09-09 additions (8 min)

Everything in this block is new since the rest of this file was written, and
none of it is covered above. Six of the nine steps are about a *mode* or a
*refusal* -- states and non-events -- which is exactly the category no automated
test can sign off, because the failure is not a wrong value but a silence you
have to notice.

**L-90. The Typing Mode cell tells the truth about overtype**
- Do: type `ABCDEF`, press **Home**. Press **Ctrl+Alt+Shift+W**. Type `x`.
  Then **F6** and arrow to **Typing Mode**.
- Pass: you heard **"Overwrite mode on"**; the line now reads `xBCDEF` (the `A`
  was replaced, not pushed along); and the cell says **Overwrite**.
- Fail if the cell and the typing disagree in either direction. That
  disagreement is the bug this feature was built to fix and it is invisible
  without checking both.
- [ ] pass  [ ] fail: ______

**L-91. The Insert key moves the cell too**
- Do: with your screen reader's modifier *not* set to Insert (or using the
  laptop layout), press **Insert** once. **F6**, arrow to **Typing Mode**.
- Pass: the cell has changed. QUILL Lite does not claim the Insert key -- the
  editing control answers it -- but the cell must follow it.
- If your reader uses Insert as its modifier, skip and note "skipped": that is
  the expected experience and not a failure.
- [ ] pass  [ ] fail: ______  [ ] skipped

**L-92. Tab Mode, and Shift+Tab out of it**
- Do: on a line reading `hello`, press **Tab**. Then **Ctrl+Alt+Shift+I** and
  press **Tab** again. Then **Shift+Tab**.
- Pass: the first Tab typed a tab character. After the toggle you heard
  **"Tab key indents the line"**, and the second Tab spoke a *depth* -- e.g.
  **"1 tab, 4 spaces"** -- and said it **once**, not twice. Shift+Tab spoke a
  smaller depth.
- [ ] pass  [ ] fail: ______

**L-93. Describe Indent Depth answers on demand**
- Do: put the cursor on a line indented with four spaces. Press
  **Ctrl+Alt+Shift+V**. Then move to an unindented line and press it again.
- Pass: **"4 spaces"**, then **"No indentation"**. The second one matters most:
  a command that goes quiet when the answer is "none" is indistinguishable from
  a key that is not bound.
- [ ] pass  [ ] fail: ______

**L-94. Bookmarks and your place survive closing the file**
- Do: open a long saved file. Press **Ctrl+Shift+3** somewhere in the middle,
  move to a different place, then **Ctrl+W** and reopen the file.
- Pass: the cursor is roughly where you left it, and **F2** takes you to
  bookmark 3.
- Also check: no new file has appeared next to your document on disk.
- [ ] pass  [ ] fail: ______

**L-95. Go Back returns you from a jump**
- Do: from partway through a document, press **Ctrl+G** and go to line 1. Then
  press **Alt+Left**. Then **Alt+Left** again.
- Pass: the first takes you back where you were and says **"Went back"**; the
  second says **"No earlier place"** rather than going silent.
- [ ] pass  [ ] fail: ______

**L-96. Earlier Versions lists and restores**
- Do: switch **Timestamped backups** on in **View > Customize Features**. Save a
  file three times, changing it each time. Press **Ctrl+Alt+Shift+E**.
- Pass: a list reading like **"Today at 4:12 PM - 120 words"**, newest first,
  arrowable. Choose one and press **Restore**.
- Then: the text changes, you hear that nothing is written until you save and
  that Ctrl+Z undoes it -- and **Ctrl+Z** does.
- [ ] pass  [ ] fail: ______

**L-97. Heading promote, demote, and section move**
- Do: in a **plain text** document type three Markdown headings with a line of
  body under each. On the second, press **Alt+Shift+Right**, then
  **Alt+Shift+Left** twice, then **Alt+Shift+Up**.
- Pass: **"Heading 3"**, **"Heading 2"**, **"Already Heading 1"** (not silence),
  and the section moved above the first one with something spoken.
- Then: in a **rich text** document press **Alt+Shift+Up**. Pass: it says
  section moves are for plain text documents rather than doing nothing.
- [ ] pass  [ ] fail: ______

**L-98. The portable copy leaves nothing behind**
- Do: this one needs the **portable** zip, not the installer. Extract it to a
  USB stick or any folder, run `QuillLite.exe`, change a setting, type
  something, and close.
- Pass: `data\QuillLite` inside the bundle now has a `settings.json`, and
  **no** `QUILL Lite` folder has appeared in `%LOCALAPPDATA%` on that machine.
- This is the one step worth running on a computer that has never had QUILL Lite
  on it, because that is the only place the old behaviour was visible.
- [ ] pass  [ ] fail: ______

---

## Block P -- The 2026-09-10 additions (9 min)

Three features and one fix, and every one of them is here for the same reason as
Block O: what would be wrong is a *silence* or a *state*, not a wrong value.
A machine can check that the Keyboard Manager stores what it was told; only a
person can check that pressing the key afterwards does the thing.

**L-99. The Keyboard Manager finds a command, and says what a key does**
- Do: **Ctrl+Alt+Shift+R**. Type `sort lines`. Listen to the count line under
  the box, then press **Down** into the list.
- Pass: focus lands in the search box on opening; the count says how many
  commands are shown; **Down** puts you on the first matching row, and the row
  reads as the command *and* the key it answers to.
- Fail if the count is silent, or if Down leaves you in the box.
- [ ] pass  [ ] fail: ______

**L-100. Record a Key answers "what does this key already do?"**
- Do: press **Record a Key**. Press **Ctrl+S**. Then press
  **Ctrl+Alt+Shift+Q**.
- Pass: the first is announced as **File > Save**; the second is announced as
  **free**. Both are spoken, not merely written to the line.
- This is the question the list cannot answer by being read, which is the whole
  reason the button exists.
- [ ] pass  [ ] fail: ______

**L-101. Insert is refused, out loud, with the reason**
- Do: with Record a Key on, press **Insert**. (If your reader uses Insert as its
  modifier, press it twice quickly or use the laptop layout.)
- Pass: you hear that Insert is the key NVDA and JAWS use as their own modifier
  and QUILL Lite never binds it. **Not** a beep, and **not** silence.
- Fail if anything at all is assigned, or if nothing is said.
- [ ] pass  [ ] fail: ______

**L-102. A taken key names its owner and asks before moving**
- Do: find **Edit > Lines > Sort Lines A to Z**, press **Enter**, and press
  **Ctrl+S**. Answer the question that appears.
- Pass: the prompt *names* File > Save rather than saying "that key is taken";
  the default answer is **No**; saying yes leaves Sort Lines on Ctrl+S and File
  > Save reading as **no key** in the list.
- Then press **Reset Everything**, say yes, and **Save**. Confirm Ctrl+S saves
  again.
- Fail if the prompt does not name the command, if Enter alone moves the key, or
  if the reset does not restore it.
- [ ] pass  [ ] fail: ______

**L-103. A rebound key reaches the menu, the F1 list and the palette**
- Do: give **Tools > Change Case > UPPER CASE** the key **Ctrl+Alt+Shift+U** and
  press **Save**. Then open that menu and listen to the item; press **Ctrl+F1**
  and find the row; press **Ctrl+Shift+P** and find the command.
- Pass: all three say **Ctrl+Alt+Shift+U**, and the key works.
- Fail if any of the three still says the old key. Three readers of one list is
  the property this whole layer exists to keep.
- [ ] pass  [ ] fail: ______

**L-104. Customize Features searches, and a profile sets everything**
- Do: **Ctrl+Alt+F10**. Type `curly quotes`. Then clear the box, choose the
  **Notepad** profile, press **Use Profile**, and press **Save**.
- Pass: typing narrows the list to Autocorrect (it matches what the feature
  *does*, not only its name) and the count is announced; Use Profile announces
  how many features are on and that nothing is saved yet; after Save the Format
  menu is gone and **Tools > File Encoding and Line Endings** is still there.
- Then re-open, choose **Recommended**, Use Profile, Save.
- Fail if the encoding dialog disappeared with the Format menu -- that is the
  trade this profile exists to avoid.
- [ ] pass  [ ] fail: ______

**L-105. The status bar does not cut itself off on a narrow window**
- Do: make the window narrow -- narrow enough that thirteen cells cannot fit on
  one line. Read the bottom line of the window with **Insert+Page Down**.
- Pass: nothing is cut off. The bar is two (or three) lines tall instead, and
  every cell reads in full.
- Then **F6** and arrow to **Status Message**: whatever was last announced reads
  in full when you press **Enter** on that cell, even if the cell itself is
  shortened on screen.
- This is the one step that needs the machine the truncation was seen on. Fail
  if any cell's text ends mid-word on screen.
- [ ] pass  [ ] fail: ______

**L-106. Five features that had no switch now have one**
- Do: **Ctrl+Alt+F10**, and untick **The Command Palette**. Save. Press
  **Ctrl+Shift+P**.
- Pass: nothing happens, and the palette is gone from the menus -- the key is
  unhooked, not just the row hidden.
- Turn it back on and confirm it returns.
- Repeat for **Describe Character** if you have a moment; the other three
  (Matches, Go Back and Go Forward, Text size) work the same way.
- [ ] pass  [ ] fail: ______

**L-107. Check for Updates answers, either way**
- Do: **Ctrl+Alt+U** (Help > Check for Updates...).
- Pass: a dialog either says you are up to date, or opens on **what changed**
  in the newer version with **Update** and **Close** beside it. Focus lands in
  the notes, not on a button, so the first thing read is the release notes.
- Pass: **Escape** closes it and downloads nothing.
- [ ] pass  [ ] fail: ______

**L-108. The daily look is silent**
- Do: with "Look for updates when QUILL Lite starts" ticked in Settings, close
  QUILL Lite and open it again. Then unplug the network and open it again.
- Pass: nothing is said either time -- no "checking", no "up to date", no
  network error. A launch is not the place to report that nothing happened.
- [ ] pass  [ ] fail: ______

**L-109. The spelling context menu is one submenu, named after the word**
- Do: type a misspelled word, leave the cursor in it and press the Applications
  key (or Shift+F10). Arrow down once, then Right.
- Pass: the first row reads as a submenu named for the word -- *Spelling:
  "wrold"* -- and opening it lands on the first suggestion. Enter replaces the
  word and says so. On a correctly spelled word there is no Spelling row at
  all, and the popup starts at Undo either way.
- [ ] pass  [ ] fail: ______

**L-110. Insert Special Character reads back what it inserted**
- Do: **Insert > Special Character...** (Ctrl+Shift+F2). Focus lands in
  the search box. Type `em dash`, press Enter to move into the list, and press
  Enter again on the first row.
- Pass: the reader names the dialog, then the search box; Enter moves to the
  list and the row reads as its character, its name and its code point; the
  second Enter closes the dialog and QUILL Lite says "Inserted", the character,
  U+2014 and "Em dash". Escape at any point says nothing and inserts nothing.
- [ ] pass  [ ] fail: ______

**L-111. The picker can be browsed as well as searched**
- Do: open it again, leave the search box empty and Shift+Tab (or Alt+G) to
  **Group**. Arrow down to "Accented letters, small", then Tab to
  **Characters** and arrow through a few rows.
- Pass: each group change refills the list; the Description pane below reads
  out the full detail of whichever row you are on; and the status line says how
  many characters are in view. Nothing is spoken over the top of the list.
- [ ] pass  [ ] fail: ______

**L-112. A code point typed into the search box finds its character**
- Do: open it, type `2014`, then clear it and type `U+00A9`, then clear it and
  type `1F600`.
- Pass: the first result each time is the em dash, the copyright sign and the
  grinning face -- the last one proving a code point outside every group still
  resolves. Then type `zzzz`: the status line says nothing matched, and the
  list is empty rather than stale.
- [ ] pass  [ ] fail: ______

**L-113. A heading says it is a heading**
- Do: in a **rich text** document type three lines, make the second one a
  Heading 2 (Ctrl+Alt+2), then arrow down onto it from the line above, arrow
  right a few characters along it, arrow back off it and onto it again.
- Pass: arriving on the line says **"Heading 2"** and nothing else -- not the
  text of the heading, which your reader has just read. Moving *along* the
  heading says nothing further. Leaving and returning says it again.
- Pass: the cue arrives **after** your reader has read the line, not on top of
  it. If it cuts the line off, that is a fail and the finding to write down.
- Pass: applying Ctrl+Alt+2 in the first place says "Heading 2" once, not
  twice.
- [ ] pass  [ ] fail: ______

**L-114. The same is true of a plain-text document**
- Do: switch to plain text (Alt+Shift+F), type `## Section two` on its own
  line with ordinary text above and below, and arrow onto it.
- Pass: "Heading 2", on the same terms as L-113.
- Do: with the cursor above it, press Ctrl+Alt+H for Next Heading, then
  Ctrl+Alt+L for the headings list.
- Pass: both work. Neither says "Headings are only available in rich text" --
  that refusal was the bug. The list offers the Markdown headings and Enter
  moves to the one you pick.
- Do: open a document that has no headings at all and press Ctrl+Alt+H.
- Pass: "No next heading" -- a sentence, not silence.
- Do: press F6 for the status bar and arrow to the **Heading** cell, with the
  cursor first on `## Section two` and then on an ordinary line.
- Pass: "Heading 2", then "Body text". It used to read "Not in rich text",
  which was wrong in a document that has headings and a cell whose Enter key
  lists them.
- [ ] pass  [ ] fail: ______

**L-115. Announce Headings can be turned off, and says so**
- Do: with the cursor on a heading, press **Ctrl+Alt+F3**, then arrow off the
  heading and back onto it. Press Ctrl+Alt+F3 again.
- Pass: the first press says "Headings will not be announced" and the heading
  is then silent on arrival; the second says "Headings announced on arrival"
  and it comes back. **View ▸ Announce Headings** shows a tick that matches.
- Pass: closing and reopening QUILL Lite remembers the choice.
- [ ] pass  [ ] fail: ______

**L-116. A shell script is not a document full of headings**
- Do: open (or paste and save as) a `.sh` or `.py` file with several `#`
  comment lines. Arrow down through it, then press Ctrl+Alt+L.
- Pass: no comment is announced as a heading, and the headings list says there
  are none. Then do the same in a `.md` or `.txt` file with `## Section` lines:
  those *are* headings, announced and listed.
- [ ] pass  [ ] fail: ______

**L-117. Nothing new is chatty**
- Do: type a paragraph of ordinary prose, arrowing about in it; then put the
  cursor in a heading and delete the line above it.
- Pass: body text is silent throughout. Deleting a line above a heading does
  **not** announce the heading -- the text moved, you did not.
- [ ] pass  [ ] fail: ______

---

## Block Q -- Markup, lists and the four kinds of document (14 min)

Everything in this block is a *sentence* or a *state*, which is why none of it
is in the test suite. A machine can check that `list_context_at` counts four
items; only a person can check that you actually hear "Bulleted list, 4 items"
and hear it once.

Have three files ready for this block: **`notes.md`**, **`page.html`** and
**`build.py`**, each containing a line of ordinary text. Create them from
QUILL Lite with **Ctrl+Shift+S** if you have none.

### The language, and the ring

**L-118. The file name decides the language, and the status bar says so**
- Do: open `notes.md`. Press **F6**, arrow to the **Format** cell.
- Pass: the cell reads **Markdown**. Repeat with `page.html` (**HTML**) and
  `build.py` (**Plain text**).
- Fail if any of the three reads "Plain text" when it should not -- that cell is
  the one place somebody checks what kind of document they are in.
- [ ] pass  [ ] fail: ______

**L-119. Alt+Shift+F rings through all four kinds**
- Do: in `build.py`, press **Alt+Shift+F** four times, listening to each.
- Pass: you hear **Markdown**, then **HTML**, then the rich-text switch, then
  back to **Plain text**. Every stop says its own name.
- Fail if it toggles between two states only -- that is the old behaviour, and
  it means three of the four kinds are unreachable from the keyboard.
- [ ] pass  [ ] fail: ______

**L-120. Ringing between the three plain kinds changes nothing in the document**
- Do: in `notes.md`, type `hello`, then press **Alt+Shift+F** twice (to HTML
  and on to plain text, avoiding the rich stop).
- Pass: the text is still exactly `hello`, and the document is **not** marked
  modified. Only what the keys write changed.
- [ ] pass  [ ] fail: ______

**L-121. Enter on the Format cell does the same ring**
- Do: **F6**, arrow to **Format**, press **Enter**.
- Pass: you hear the next kind, and arrowing back to the cell reads the new
  value. **Fail if the cell still reads what it read before** -- that was the
  reported defect.
- [ ] pass  [ ] fail: ______

**L-122. Ctrl+Alt+F6 goes straight to one**
- Do: in `build.py`, press **Ctrl+Alt+F6**, arrow to **HTML**, press **Enter**.
- Pass: the chooser names all three, marks which one the file name implies, and
  the confirmation says **"Document language: HTML"**.
- [ ] pass  [ ] fail: ______

### What the keys write

**L-123. Ctrl+B writes Markdown in a Markdown document**
- Do: in `notes.md`, type `hello world`, select `world` (**Shift+Ctrl+Left**),
  press **Ctrl+B**.
- Pass: the line reads `hello **world**`, and you hear **"Bold in Markdown"** --
  not "Bold on". Nothing went bold; two asterisks appeared, and the sentence has
  to say which of the two happened.
- [ ] pass  [ ] fail: ______

**L-124. Ctrl+B writes HTML in an HTML document, and uses `<strong>`**
- Do: the same in `page.html`.
- Pass: `hello <strong>world</strong>`, announced as **"Bold in HTML"**.
- Fail if it wrote `<b>`. `<strong>` carries importance into the accessibility
  tree and `<b>` carries only a typeface; an editor built for listeners must not
  emit the presentational one.
- [ ] pass  [ ] fail: ______

**L-125. With nothing selected the cursor lands between the tags**
- Do: in `page.html`, on an empty line, press **Ctrl+I**, then type `word`.
- Pass: the line reads `<em>word</em>`. Fail if it reads `<em></em>word` -- you
  cannot see where the caret went, so this has to be right without checking.
- [ ] pass  [ ] fail: ______

**L-126. Italic and underline follow the same rule**
- Do: in `notes.md` select a word and press **Ctrl+I**; then another and
  **Ctrl+U**.
- Pass: `*word*` and `<u>word</u>`. Underline is `<u>` in both languages --
  Markdown has no spelling of its own for it.
- [ ] pass  [ ] fail: ______

**L-127. A plain document refuses, and offers both ways out**
- Do: in `build.py`, select a word and press **Ctrl+B**.
- Pass: nothing is inserted, and you hear that this document has no formatting,
  **Control Shift M** for rich text, **or Control Alt F6** to write Markdown or
  HTML in it. Both routes, because either could be what was meant.
- Fail if it silently inserted asterisks into a Python file.
- [ ] pass  [ ] fail: ______

**L-128. The heading keys write the document's own headings**
- Do: on a line of text in `notes.md` press **Ctrl+Alt+2**. Then the same on a
  line in `page.html`.
- Pass: `## your text` and `<h2>your text</h2>`. Both announce **"Heading 2"**.
- [ ] pass  [ ] fail: ______

**L-129. Applying a level rewrites the line rather than stacking on it**
- Do: put the cursor on a line reading `### Notes` in `notes.md`. Press
  **Ctrl+Alt+2**.
- Pass: the line reads `## Notes`. **Fail if it reads `## ### Notes`** -- that
  renders as a Heading 2 whose text starts with three hashes, nothing announces
  it, and you find out in the published document.
- [ ] pass  [ ] fail: ______

**L-130. An HTML heading keeps its id**
- Do: type `<h3 id="install">Setup</h3>` in `page.html`, put the cursor in it,
  press **Ctrl+Alt+1**.
- Pass: `<h1 id="install">Setup</h1>`. The `id` is very often the anchor
  somebody else's link points at.
- [ ] pass  [ ] fail: ______

**L-131. Body text takes the marker back off, and says so when there is none**
- Do: on the `## Notes` line press **Ctrl+Alt+0**. Then press it again.
- Pass: first it becomes `Notes` and says **"Body text"**; the second press says
  **"Already body text"** rather than nothing.
- [ ] pass  [ ] fail: ______

**L-132. Alt+Shift+Right walks HTML headings**
- Do: cursor in an `<h2>` in `page.html`, press **Alt+Shift+Right**.
- Pass: `<h3>`, announced as "Heading 3". Fail if it says "Put the cursor on a
  heading line" -- that means it went looking for hashes an HTML file will never
  contain.
- [ ] pass  [ ] fail: ______

### The Insert menu

**L-133. Insert is a top-level menu, before Format**
- Do: press **Alt** and arrow along the menu bar.
- Pass: the order is File, Edit, View, **Insert**, Format, Navigate, Tools,
  Window, Help. Every item in Insert reads a key after its name.
- [ ] pass  [ ] fail: ______

**L-134. The wrong tag picker is dimmed, not missing**
- Do: in `notes.md` open **Insert** and arrow to **HTML Tag**. Then do the same
  in `page.html` with **Markdown Tag**.
- Pass: in each case the row is **present and announced as unavailable**. Fail
  if the row has vanished -- a missing row leaves somebody hunting the menus for
  a feature they know the app has.
- [ ] pass  [ ] fail: ______

**L-135. Pressing the key anyway explains rather than doing nothing**
- Do: in `notes.md` press **Ctrl+Alt+O** (Insert HTML Tag).
- Pass: you hear that it needs an HTML document, that this one is Markdown, and
  that **Control Alt F6** changes that. Nothing is inserted.
- [ ] pass  [ ] fail: ______

**L-136. The HTML picker searches by what a tag does**
- Do: in `page.html` press **Ctrl+Alt+O**. Type `dropdown`. Press **Down**.
- Pass: focus starts in the search box; typing filters; **Down** (or Enter)
  moves you into the results, and `select` is in them. The list announces how
  many matches there are as you arrive on it.
- [ ] pass  [ ] fail: ______

**L-137. Attributes are optional and Enter skips them**
- Do: continue from L-136 -- choose `select`, then press **Enter** on the empty
  attribute box.
- Pass: `<select></select>` is inserted with the cursor between the tags, and
  you hear **"Inserted HTML tag select"**.
- [ ] pass  [ ] fail: ______

**L-138. Attributes are parsed from a semicolon list**
- Do: **Ctrl+Alt+O**, choose `div`, type `class=note; id=main`.
- Pass: `<div class="note" id="main"></div>`.
- [ ] pass  [ ] fail: ______

**L-139. The Markdown picker asks for a link address**
- Do: in `notes.md` press **Ctrl+Alt+I**, type `link`, choose **Link**, and put
  an address in.
- Pass: a Markdown link is inserted and announced. Escaping the address box
  cancels cleanly rather than inserting a half-built link.
- [ ] pass  [ ] fail: ______

**L-140. The emoji picker is searchable and describes what it inserts**
- Do: press **Alt+.**. Type `party`. Arrow through the results.
- Pass: each row reads as a name rather than an unlabelled character, and the
  description pane changes as you arrow. Insert one: you hear **"Inserted ..."**
  with the emoji's *name*.
- Fail if the inserted character is announced as nothing, or if the list reads
  as blank rows.
- [ ] pass  [ ] fail: ______

**L-141. The emoji picker works in a rich text document**
- Do: **Ctrl+Shift+N** for a new rich document, then **Alt+.**.
- Pass: it opens and inserts. An emoji is a character, not markup.
- [ ] pass  [ ] fail: ______

### Lists

Paste this into `notes.md` for the next few:

```
Shopping notes.

- fruit
    - apple
    - pear
- veg

That is all.
```

**L-142. Entering a list names it and counts it**
- Do: put the cursor on "Shopping notes", then arrow down to `- fruit`.
- Pass: you hear **"Bulleted list, 2 items"** -- two, because that is how many
  there are *at this level*. Fail if it says 5.
- [ ] pass  [ ] fail: ______

**L-143. Going a level down says the level and the new count**
- Do: arrow down to `- apple`.
- Pass: **"Level 2, 2 items"**.
- [ ] pass  [ ] fail: ______

**L-144. Moving between items of one list is silent**
- Do: arrow from `- apple` to `- pear`.
- Pass: **nothing** beyond your reader reading the line. A cue per item would
  make a list unusable.
- [ ] pass  [ ] fail: ______

**L-145. Coming back up a level says so**
- Do: arrow down from `- pear` to `- veg`.
- Pass: **"Level 1, 2 items"**.
- [ ] pass  [ ] fail: ______

**L-146. Leaving says so**
- Do: arrow down to "That is all".
- Pass: **"Out of list"**.
- [ ] pass  [ ] fail: ______

**L-147. Numbered lists are named differently**
- Do: replace the dashes with `1.`, `2.` and arrow in again.
- Pass: **"Numbered list, ..."**. Order is meaning; the two must not sound the
  same.
- [ ] pass  [ ] fail: ______

**L-148. HTML lists behave identically**
- Do: in `page.html`, type `<p>Before.</p>`, then a `<ul>` with two `<li>`
  rows, then `<p>After.</p>`. Arrow through it.
- Pass: "Bulleted list, 2 items" going in, "Out of list" coming out.
- [ ] pass  [ ] fail: ______

**L-149. A definition list names its two halves**
- Do: in `notes.md`, type a line `Quill`, then under it `: the editor`, then a
  blank line, then `Lite` and `: the small one`. Arrow through all four lines.
- Pass: **"Definition list, 2 terms"** entering, then **"Definition"** and
  **"Term"** as you alternate. Which half you are standing in decides what the
  words mean.
- [ ] pass  [ ] fail: ______

**L-150. A code fence is not a list**
- Do: in `notes.md`, put a fenced block containing `- not a bullet` and arrow
  through it.
- Pass: **silence**. A dash in a code sample is a sample.
- [ ] pass  [ ] fail: ______

**L-151. A horizontal rule is not a one-item list**
- Do: put `---` on a line of its own between two paragraphs and arrow onto it.
- Pass: **silence**.
- [ ] pass  [ ] fail: ______

**L-152. A plain document never hears about lists**
- Do: in `build.py`, put `- not a bullet` on a line and arrow onto it.
- Pass: **silence**. A letter is full of hyphens and a script is full of flags.
- [ ] pass  [ ] fail: ______

**L-153. The List cell says which item you are on**
- Do: with the cursor on `- pear`, press **F6** and arrow to **List**.
- Pass: it reads something like **"Bulleted list, 2 of 2, level 2"**. This is
  the fact the speech deliberately does not give you on every arrow press.
- [ ] pass  [ ] fail: ______

**L-154. Enter on the List cell turns the cue off, and says so**
- Do: press **Enter** on that cell, then Escape back and arrow into a list.
- Pass: **"Lists will not be announced"**, and then silence in the list. Press
  **Ctrl+Alt+F5** to bring it back: **"Lists announced as you enter them"**.
- [ ] pass  [ ] fail: ______

**L-155. The two switches are independent**
- Do: turn **lists** off (**Ctrl+Alt+F5**) and arrow onto a heading. Then turn
  lists back on, turn **headings** off (**Ctrl+Alt+F3**), and arrow into a list.
- Pass: headings still announce in the first case; lists still announce in the
  second. **Fail if either switch silences the other** -- that is the whole
  reason there are two of them.
- [ ] pass  [ ] fail: ______

### Where the heading level goes

**L-156. A heading says its level first, with its own words**
- Do: arrow onto a heading.
- Pass: you hear **"Heading 2, Installing"** -- the level, then the text, as one
  sentence, and your reader does not then read the line a second time.
- [ ] pass  [ ] fail: ______

**L-157. Ctrl+Home onto a heading announces it** *(the reported defect)*
- Do: with the cursor somewhere in the middle of a document whose first line is
  a heading, press **Ctrl+Home**.
- Pass: you hear **"Heading 1, ..."**. Fail if you hear only the line -- that
  is the defect, and it is caused by the reader cancelling a cue that was
  queued behind it.
- Try the same with **Ctrl+End**, a search hit (**F3**) and a bookmark jump.
- [ ] pass  [ ] fail: ______

**L-158. The other order is still available**
- Do: **Ctrl+,** for Preferences, find **Say a heading's level**, choose
  **After the text**, save. Arrow onto a heading.
- Pass: your reader reads the line, then you hear **"Heading 2"** alone. Put it
  back to **Before the text** afterwards.
- [ ] pass  [ ] fail: ______

### The status bar

**L-159. F6 leaves the status bar as well as entering it** *(reported)*
- Do: press **F6**, arrow to any cell, press **F6** again. Then repeat with
  **Shift+F6**.
- Pass: you are back in your document both times. Escape still works too.
- Fail if F6 does nothing once you are in the bar.
- [ ] pass  [ ] fail: ______

**L-160. Nothing new is chatty**
- Do: type two paragraphs of ordinary prose in `notes.md`, arrowing about. Then
  put the cursor inside a list and type a sentence into an item.
- Pass: body text is silent; typing inside a list item says nothing; deleting
  the line above a list does **not** announce the list.
- This is the one that decides whether the whole block shipped or should not
  have: over-announcing is absorbed as "this app is chatty" and never filed.
- [ ] pass  [ ] fail: ______


### Form fields, inserted whole

The wiring is the whole point of these and none of it is visible, so every step
here is "read the markup back and check a pair of values match".

**L-161. A dropdown arrives labelled and wired**
- Do: in `page.html` press **Ctrl+Alt+O**, type `dropdown`, choose **Form field:
  dropdown (select)**.
- Pass: you get a `<label>`, a `<select>`, and options -- and the label's
  `for="..."` is **the same string** as the select's `id="..."`. Read both
  aloud and compare them character by character.
- Fail if they differ, or if either is missing: a `for` that points at nothing
  renders identically to one that works, and the field reads as unlabelled.
- [ ] pass  [ ] fail: ______

**L-162. The dropdown cannot submit an answer nobody gave**
- Pass: the first `<option>` has `value=""`. A select whose first option is a
  real choice submits that choice when nobody touches it.
- [ ] pass  [ ] fail: ______

**L-163. A radio group is a group**
- Do: **Ctrl+Alt+O**, type `radio`, choose **Form field: radio group**.
- Pass: a `<fieldset>`, a `<legend>`, three radios that **all share one
  `name`**, and **exactly one** `checked`.
- Fail if the names differ -- then they are not a group and all three can be on
  at once, which looks identical on screen.
- [ ] pass  [ ] fail: ______

**L-164. A selection becomes the label, and the id follows it**
- Do: type `Postcode`, select it, then **Ctrl+Alt+O** and choose **Form field:
  text**.
- Pass: the label reads Postcode, and both `id` and `for` read `postcode`.
- [ ] pass  [ ] fail: ______

**L-165. A second field does not reuse the first one's id** *(the silent one)*
- Do: insert **Form field: email** twice in the same document.
- Pass: the second reads `email-2` (or similar) in **both** its `id` and its
  `for`. Fail if both fields claim `id="email"` -- the page looks perfect, and
  the only symptom is that clicking the second label focuses the first field.
- [ ] pass  [ ] fail: ______

**L-166. The validated-field pattern is wired three ways**
- Do: **Ctrl+Alt+O**, type `error message`, choose **Form field: required, with
  hint and error**.
- Pass: `aria-describedby` names **two** ids, both of which exist in what was
  inserted; there is an `aria-invalid="false"`; and the empty error paragraph
  carries `role="alert"`.
- [ ] pass  [ ] fail: ______

**L-167. A whole control does not ask for attributes**
- Do: choose any **Form field:** row.
- Pass: it inserts immediately -- no attribute box. Then choose a bare tag
  (`div`): the attribute box **does** appear, and Enter on it empty inserts
  `<div></div>`.
- [ ] pass  [ ] fail: ______

**L-168. The pickers are complete**
- Do: **Ctrl+Alt+O** and search in turn for `glossary`, `acronym`, `image
  caption`, `table header`, `subtitles`, `divider`.
- Pass: `dl`, `abbr`, `figcaption`, `thead`, `track` and `hr` are each in the
  first few results. Then **Ctrl+Alt+I** in `notes.md` and confirm
  **Underline**, **Strikethrough**, **Horizontal Rule** and **Definition List**
  are all offered.
- [ ] pass  [ ] fail: ______

**L-169. The emoji catalogue is current**
- Do: **Alt+.** and search for `bags under eyes`, then `fingerprint`, then
  `splatter`.
- Pass: each is found, with a written description. These are Unicode Emoji 16.0
  additions -- the newest published set -- so finding them is the fastest way to
  confirm the shipped catalogue is not a release behind.
- [ ] pass  [ ] fail: ______

### Saving HTML as Markdown (2026-09-15)

The **Markdown** row in Save As was taken out once because it did not convert
anything -- it wrote the same text under a different name. It is back because
it converts now, so what these three check is that the promise the type list
makes is kept.

**L-170. An HTML document saved as .md really becomes Markdown**
- Do: open `page.html` and put a heading, a bold word and a two-item list in it
  as HTML (`<h1>Title</h1>`, `<p>Some <strong>bold</strong> text.</p>`,
  `<ul><li>one</li><li>two</li></ul>`). Press **Ctrl+Shift+S**, choose
  **Markdown (*.md)** in the type list, and save as `page.md`.
- Pass: you hear **"Converted HTML to Markdown"**. The document in front of you
  now reads `# Title`, `Some **bold** text.` and `- one` / `- two`; there is no
  `<h1>` anywhere. Open `page.md` in Notepad and it matches what you are
  looking at.
- Fail if the file contains any HTML tag, or if the window still shows tags
  while the file does not -- a `.md` whose window holds HTML is the same lie in
  the other direction.
- [ ] pass  [ ] fail: ______

**L-171. The Format cell follows the new name**
- Do: straight after L-170, press **F6** and arrow to the **Format** cell.
- Pass: it reads **Markdown**. The document was pinned to HTML a moment ago, and
  the file name is what decides from here.
- [ ] pass  [ ] fail: ______

**L-172. Plain text saved as .md is left exactly alone**
- Do: in a **plain text** document type `2 < 3 and 4 > 1`, then **Ctrl+Shift+S**
  and save as `notes-plain.md`.
- Pass: nothing is announced about converting, and the file contains
  `2 < 3 and 4 > 1` character for character -- the `<` and `>` are untouched.
- Fail if the angle brackets have been escaped, swallowed or turned into an
  entity: plain text saved as Markdown is already what it claims to be, and
  running it through an HTML converter can only lose something.
- [ ] pass  [ ] fail: ______

**L-173. Rich text does not offer Markdown**
- Do: in a **rich text** document press **Ctrl+Shift+S** and read the type list.
- Pass: it offers **Rich Text**, **Text files** and **All files** -- and no
  Markdown row. Rich to Markdown would mean guessing which bold runs were meant
  as headings; flatten to plain text first (the dialog asks) and the Markdown
  row is there.
- [ ] pass  [ ] fail: ______

### The save path keeps what you had (2026-09-17)

Four bugs on one path, and every one of them loses work quietly. Run this block
on a copy of a real file, not a scratch one -- the failures here are the kind
you only notice a week later.

**L-174. A failed Save As leaves the window alone**
- Do: open any `.rtf` and put a heading and a bold word in it. Open the same
  folder in another program that locks files, or make the target read-only --
  the simplest way is to save once as `locked.txt`, then set that file
  read-only in Explorer. Now in QUILL Lite press **Ctrl+Shift+S**, choose
  **Text files**, and save over `locked.txt`. Answer **Yes** to "Saving as
  plain text removes all formatting".
- Pass: you hear that the save failed and names the file. The document in front
  of you is **still rich text** -- the heading is still a heading, the bold word
  is still bold, the status bar's Format cell still says Rich Text -- and
  **Ctrl+Z** still has your edits in it.
- Fail if the window is now plain text. That is the bug: the conversion used to
  happen before the write, so a failed write left flattened text under the
  original name, with the next Ctrl+S ready to write it over the `.rtf`.
- [ ] pass  [ ] fail: ______

**L-175. A failed HTML-to-Markdown save leaves the window alone**
- Do: the same, from an HTML document saving over a read-only `.md`.
- Pass: the save fails, and the document is still HTML -- tags and all. Nothing
  is announced about converting.
- [ ] pass  [ ] fail: ______

**L-176. A character the encoding cannot hold is asked about**
- Do: open a file saved as **Windows-1252** (or use Tools ▸ File Encoding and
  Line Endings to set it to Windows-1252 and save once). Type an em dash — this
  one — and an emoji. Press **Ctrl+S**.
- Pass: a question appears before anything is written, and it counts them:
  "2 characters cannot be saved as Windows-1252. Save as UTF-8 instead?" with
  **Yes**, **No** and **Cancel**.
- Fail if it saves without asking. Those characters used to become question
  marks with "Saved" announced as though nothing had happened.
- [ ] pass  [ ] fail: ______

**L-177. Yes keeps the characters and the status bar agrees**
- Do: answer **Yes** to L-176, then press **F6** and arrow to the **Encoding**
  cell.
- Pass: the file holds the em dash and the emoji, and the cell reads **UTF-8**.
  The document really is UTF-8 from now on, so the cell has to say so.
- [ ] pass  [ ] fail: ______

**L-178. Cancel writes nothing**
- Do: repeat L-176 and answer **Cancel**.
- Pass: you hear "Save cancelled", the file on disk is unchanged, and the
  document is still marked as having unsaved changes.
- [ ] pass  [ ] fail: ______

**L-179. A recovered file keeps its own encoding and line endings**
- Do: open a `.txt` saved with **Unix** line endings (any file from a git
  checkout). Type a sentence but do **not** save. Wait forty seconds so the
  copy-aside has run. Now end the QUILL Lite process from Task Manager. Start
  QUILL Lite again and let it restore the document. Press **Ctrl+S**.
- Pass: press **F6** and the **Line Endings** cell reads **LF** before you save,
  and the saved file still has Unix line endings afterwards.
- Fail if it reads CRLF, or the saved file gained Windows line endings. The copy
  kept aside is always written one way; what the document *was* is recorded
  beside it, and that is what must come back.
- [ ] pass  [ ] fail: ______

**L-180. A recovery that fails takes nothing**
- Do: after a crash as in L-179, and **before** starting QUILL Lite, open
  `%LOCALAPPDATA%\QuillLite\recovery` and make the copy's content file
  unreadable -- the simplest way is to open it in another program that holds an
  exclusive lock, or deny yourself read access in its Properties ▸ Security.
  Now start QUILL Lite.
- Pass: you hear that it could not be recovered and is still saved aside. The
  window is **untitled** -- it has not taken the original file's name -- and it
  is not marked as changed. The copy is still on disk, and the next launch
  offers it again.
- Fail if the empty window carries the real file's name. Closing that window and
  answering "No" used to delete the only copy of the work.
- [ ] pass  [ ] fail: ______

### The mode switch converts rather than flattens (2026-09-17)

**L-181. Leaving rich text turns the formatting into Markdown**
- Do: in a **rich text** document write a line, make it **Heading 2**
  (Ctrl+Alt+2), write a second line with a **bold** word in it, and a two-item
  bullet list. Press **Alt+Shift+F** until you are asked about leaving rich
  text, and answer **Yes**.
- Pass: the heading line now reads `## ` followed by its text, the bold word
  reads `**word**`, and the list lines begin `- `. You hear "Plain text mode".
- Fail if the text is there with none of the marks. That is the old behaviour:
  it took the letters and left everything else.
- [ ] pass  [ ] fail: ______

**L-182. The document is then called Markdown**
- Do: straight after L-181, press **F6** and arrow to the **Format** cell.
- Pass: it reads **Markdown**. A buffer full of `##` that the cell calls plain
  text is the cell lying about the one thing it is for.
- [ ] pass  [ ] fail: ______

**L-183. The headings are still headings afterwards**
- Do: straight after L-182, press **Ctrl+Alt+L** for the headings list.
- Pass: the heading from L-181 is in it. This is the point of converting rather
  than flattening -- heading navigation, the list and the outline all keep
  working because the structure survived in a form they can read.
- [ ] pass  [ ] fail: ______

**L-184. Saying no changes nothing at all**
- Do: repeat L-181 and answer **No**.
- Pass: the document is still rich text, the heading is still a heading, and the
  Format cell still reads Rich text. Nothing was announced about plain text.
- [ ] pass  [ ] fail: ______

**L-185. Markdown becomes real formatting going the other way**
- Do: in a **Markdown** document (`notes.md`) type `## Title`, a blank line, and
  `Some **bold** text.` Ring with **Alt+Shift+F** to rich text.
- Pass: the title line is a real heading -- arrow onto it and you hear
  "Heading 2" -- and the bold word is really bold with no asterisks on screen.
- Fail if `##` and `**` are still sitting there. The document said it was rich
  text and nothing in it was.
- [ ] pass  [ ] fail: ______

**L-186. A plain text file is not read as markup**
- Do: in a **plain text** document (`list.txt`, with the Format cell reading
  Plain text) type `buy 2 * 3 eggs`. Ring to rich text.
- Pass: the line is unchanged, character for character. The asterisk is an
  asterisk.
- Fail if anything became bold or italic. Guessing that a shopping list is
  markup is a decision with no way back from it.
- [ ] pass  [ ] fail: ______

**L-187. A document that changes mode keeps its name**
- Do: open `notes.txt`, ring to **rich text**, then press **Ctrl+S**.
- Pass: the Save As box opens with **notes.rtf** already filled in -- the same
  folder, the same stem, the right suffix. Accept it and the file is written.
- Fail if the box is empty, or proposes `notes.txt`, or if Ctrl+S writes RTF
  into `notes.txt` without asking. The window used to forget the file
  altogether.
- [ ] pass  [ ] fail: ______

**L-188. The warning names what will not survive**
- Do: open an `.rtf` that contains a **table** (make one in WordPad or Word and
  save it as RTF). Open it in QUILL Lite and ring out of rich text.
- Pass: the question names it -- "Switching to plain text cannot carry: tables".
- Fail if the question is the generic one. Naming the loss before it happens is
  the difference between a warning and a formality.
- [ ] pass  [ ] fail: ______

### Selections and marks (2026-09-17)

**L-189. Go to the Start of the Selection actually goes there**
- Do: put the cursor at the start of a paragraph, press **Ctrl+Shift+H** to
  select it, then **Alt+Shift+F8**. Now press **Shift+Right** once.
- Pass: you hear "At the start of the selection", and the Shift+Right extends
  from the **beginning** of the paragraph -- one character selected, the first
  one.
- Fail if Shift+Right moves at the far end. The command used to announce an
  arrival it had not made: the call that re-selected the text put the cursor
  straight back where it came from.
- [ ] pass  [ ] fail: ______

**L-190. Every selection is announced the same way**
- Do: press in turn **Ctrl+Shift+W** (word), **Ctrl+Shift+E** (line),
  **Ctrl+Shift+H** (paragraph) and **Ctrl+Space** (sentence).
- Pass: each says what it took and how many **words** -- "Selected line, 3
  words". No character counts.
- Fail if any of them reports characters. QUILL says words and QUILL Lite said
  both, so the same key reported the same fact two ways.
- [ ] pass  [ ] fail: ______

**L-191. The F8 span is the one that says which lines**
- Do: press **F8** at the top of a paragraph, arrow down three lines, press
  **Shift+F8**.
- Pass: the sentence ends with the lines it reached -- "lines 4 to 7". This is
  the only selection that carries them, because it is the only one whose reach
  you cannot work out from its name.
- [ ] pass  [ ] fail: ______

**L-192. Reselect puts back a selection made any way at all**
- Do: press **Ctrl+Shift+H** to select a paragraph, press **Right** to throw it
  away, then **Ctrl+Shift+F8**.
- Pass: the paragraph is selected again and you hear "Reselected", with the
  same word count.
- Fail if it says there is no previous selection. Reselect used to know only
  about F8, Select Sentence and Select Block -- so the three commands people
  actually use were the three it could not undo.
- [ ] pass  [ ] fail: ______

**L-193. A mark moves with the text**
- Do: in a document of several paragraphs, put the cursor on the word starting
  the **third** paragraph and press **Ctrl+Shift+M**. Go to the very top
  (Ctrl+Home) and type three new lines. Now press **Ctrl+M**.
- Pass: the cursor is back on that same word.
- Fail if it lands three lines short. A mark used to be a bare position, so it
  pointed at whatever had since moved into that spot.
- [ ] pass  [ ] fail: ______

**L-194. Alt+Left comes back from a mark**
- Do: set a mark somewhere, move a long way off, press **Ctrl+M** to go back to
  it, then press **Alt+Left**.
- Pass: you are returned to where you pressed Ctrl+M from.
- Fail if Alt+Left goes somewhere else or does nothing. Pop Mark, the mark list
  and Ctrl+Alt+X used to move the cursor without telling the Back key.
- [ ] pass  [ ] fail: ______

**L-195. The same place cannot fill the mark ring**
- Do: press **Ctrl+Shift+M** five times without moving.
- Pass: the last one says "1 mark", not "5 marks".
- [ ] pass  [ ] fail: ______

### The Tier 2 and Tier 3 crossings (2026-09-17)

Five things QUILL had and QUILL Lite did not. Each is shared code given a door
here, so what these check is the door and the sentence, not the engine.

**L-196. Extend Selection Mode is a Shift that stays down**
- Do: put the cursor at the start of a paragraph and press
  **Alt+Shift+F9**. Now press **Down** four times, listening on each press.
  Then press **Ctrl+Shift+C** to copy.
- Pass: you hear "Extend selection mode on" with a line and column. The four
  Down presses each move one line and your screen reader does **not** say
  "selected" on any of them. The copy takes all four lines.
- Fail if the reader announces a selection on every arrow. That noise is the
  entire reason this mode exists.
- [ ] pass  [ ] fail: ______

**L-197. Page Up in Extend Selection Mode moves a real page**
- Do: in a document longer than two screens, turn the mode on at the top and
  press **Page Down** once, then **Shift+F8**-style check by copying.
- Pass: the selection reaches roughly the bottom of the visible window, not ten
  lines. Ten was hardcoded; a page is measured from your window.
- [ ] pass  [ ] fail: ______

**L-198. Down follows the line you can see, not the paragraph**
- Do: with **Word Wrap on**, write one paragraph long enough to wrap over three
  or four display lines. Put the cursor at its start, turn the mode on, and
  press **Down** once.
- Pass: the cursor moves down one *visible* line, still inside the paragraph.
- Fail if it jumps past the whole paragraph. That was the bug.
- [ ] pass  [ ] fail: ______

**L-199. Ctrl+Right stops at punctuation**
- Do: type `self.editor.SetSelection` and put the cursor at the start. Turn the
  mode on and press **Ctrl+Right** repeatedly.
- Pass: it stops at each `.` on the way -- `self`, `.`, `editor`, `.`,
  `SetSelection` -- which is what Notepad, WordPad and every other edit control
  on Windows do.
- Fail if one press takes you past the whole expression.
- [ ] pass  [ ] fail: ______

**L-200. Ctrl+Alt+F8 is the marker, not the mode**
- Do: press **Ctrl+Alt+F8**, then read the Edit ▸ Selection menu.
- Pass: it says **Toggle Selection Marker**, and the mode is on
  **Alt+Shift+F9** as its own row. Pressing Ctrl+Alt+F8 drops the F8
  marker without moving the cursor.
- Fail if one key does both jobs, or if the menu calls the marker "Extend
  Selection Mode". They are different things and QUILL uses the same two keys.
- [ ] pass  [ ] fail: ______

**L-201. The Heading Organizer lists every heading**
- Do: in a Markdown document with at least four headings at two levels, press
  **Ctrl+Alt+Shift+O**.
- Pass: a **Headings** list opens with every heading in it, each row reading
  its level and its text. Arrowing changes the preview beside it to the section
  under that heading.
- [ ] pass  [ ] fail: ______

**L-202. Tab and Shift+Tab change a heading's level**
- Do: in the organizer, arrow to a Heading 2 and press **Tab**, then
  **Shift+Tab**.
- Pass: you hear it become Heading 3 and then Heading 2 again, naming the
  heading each time.
- [ ] pass  [ ] fail: ______

**L-203. Moving a heading takes its section with it**
- Do: arrow to the second heading, press **Move Down**, then **Apply**.
- Pass: you hear where it moved to, as "3 of 7". The document now has that
  heading **and the paragraphs under it** below the section that was after it.
  One **Ctrl+Z** puts the whole thing back.
- Fail if only the heading line moved, or if undo takes several presses.
- [ ] pass  [ ] fail: ______

**L-204. Validate names what is wrong with the order**
- Do: make the first heading a Heading 2 (so the document does not start at 1)
  and press **Validate**.
- Pass: it says so, and **Apply** refuses until it is fixed.
- [ ] pass  [ ] fail: ______

**L-205. Folding says how much went with it**
- Do: in a Markdown document, put the cursor inside a section and press
  **Ctrl+Shift+Minus**.
- Pass: "Folded: 34 lines under Installing", with the real count. Pressing it
  again says "Unfolded: Installing".
- [ ] pass  [ ] fail: ______

**L-206. A folded section still reads normally**
- Do: straight after L-205, arrow **Down** through the folded section.
- Pass: every line reads exactly as it did before, and **Ctrl+F** still finds
  text inside it.
- Fail if any text is skipped. Nothing is ever hidden from the cursor -- the
  fold is a note to yourself, not a change to the document.
- [ ] pass  [ ] fail: ______

**L-207. Walking sections is the skim**
- Do: press **Ctrl+Shift+Right** several times from the top of the document.
- Pass: each stop says the heading, whether it is folded, and how many lines
  are under it. **Alt+Left** brings you back from the last jump.
- [ ] pass  [ ] fail: ______

**L-208. Snippets lists them with a preview**
- Do: press **Alt+Shift+I**.
- Pass: a **Snippets** list opens with every abbreviation, each row reading its
  trigger and the beginning of what it writes. Enter on one puts it in at the
  cursor and says "Inserted" with its name.
- Fail if the rows are triggers alone -- the trigger is the thing you came here
  because you could not remember.
- [ ] pass  [ ] fail: ______

**L-209. Print Preview answers in words**
- Do: in a document of a few pages, press **Ctrl+Alt+Shift+P**.
- Pass: you hear "N pages", the paper name and the margins, and the window
  lists each page with the first line on it. The page count matches what comes
  out if you then print.
- [ ] pass  [ ] fail: ______

**L-210. Rich text prints as rich text**
- Do: in a **rich text** document with a Heading 1, a bold word and a bullet
  list, print to PDF (or to paper).
- Pass: the heading is larger and bold on the page, the bold word is bold, and
  the list has bullets.
- Fail if everything is one size. That was true until this version, and it made
  QUILL Lite's printed output worse than its screen.
- [ ] pass  [ ] fail: ______

**L-211. The corrections come first again**
- Do: type a misspelled word, leave the cursor in it, and press the
  **Applications key**. Press **Down** once.
- Pass: you land on a **suggestion**, and Enter replaces the word. Below the
  suggestions there is one row, **Spelling Actions for "word"**, and then Undo,
  Cut, Copy and the rest -- in that order, every time.
- Fail if the first Down lands on a submenu or on Undo.
- [ ] pass  [ ] fail: ______

**L-212. F7 starts where you are and offers to wrap**
- Do: put the cursor halfway down a document with misspellings both above and
  below it, and press **F7**. Work through to the end.
- Pass: the first word it stops on is **after** the cursor, and when it runs out
  it says it is wrapping to the beginning and carries on with the ones above.
- [ ] pass  [ ] fail: ______

**L-213. A word taught in QUILL is known here at once**
- Do: with **Use QUILL's dictionary** on in Preferences and both apps open,
  teach a made-up word in QUILL. Come back to QUILL Lite, type the same word and
  wait for the live check.
- Pass: it is not reported. No restart needed.
- [ ] pass  [ ] fail: ______

**L-214. Curly quotes and em dashes are separate switches**
- Do: in Preferences, switch **Curl quotes as I type** on and **Turn two
  hyphens into an em dash** off (with Autocorrect on in Customize Features).
  Type a quote, then two hyphens.
- Pass: the quote curls; the hyphens stay two hyphens.
- [ ] pass  [ ] fail: ______

**L-215. Autocorrect never touches a configuration file**
- Do: with both switches on, open a `.json` or a `.py` and type a quote and two
  hyphens.
- Pass: both stay exactly as typed. A curly quote there is a syntax error that
  arrives silently.
- [ ] pass  [ ] fail: ______

### The tutorials (2026-09-17)

**L-216. Ctrl+Alt+F1 opens the lessons**
- Do: press **Ctrl+Alt+F1**.
- Pass: a **QUILL Lite Tutorials** window opens, listing eight lessons in two
  tracks. Arrowing reads each lesson's title, how long it takes, and what you
  will be able to do at the end.
- [ ] pass  [ ] fail: ______

**L-217. A step shows the key you actually have**
- Do: rebind **Select Paragraph** in the Keyboard Manager to something else.
  Open the tutorials, go to "Selecting more than a few words", and read its
  first step.
- Pass: the step shows **your** key, not Ctrl+Shift+H.
- Fail if it shows the shipped key. The lesson asks the command registry when
  it draws the step, which is the whole reason a step names a command rather
  than a key.
- [ ] pass  [ ] fail: ______

**L-218. Every step says what you should hear**
- Do: arrow through any lesson's steps.
- Pass: each one ends with what to listen for. A screen-reader user's
  confirmation that a step worked is a sentence, not a green tick.
- [ ] pass  [ ] fail: ______

**L-219. The book says the same thing as the window**
- Do: open the tutorial book (the button in the window, or
  `docs\tutorials.html` beside the app) and compare any lesson with the window.
- Pass: the same lessons, the same steps, in the same order. The book is
  generated from the lessons, so they cannot drift.
- Fail if any lesson is in one and not the other.
- [ ] pass  [ ] fail: ______

**L-220. It remembers where you stopped**
- Do: work three steps into a lesson, close the window, and reopen it.
- Pass: you are offered the lesson again at the step you were on.
- [ ] pass  [ ] fail: ______

### The family keymap, second pass (2026-09-17)

Three keys changed meaning in **both** editors, so these are worth a listen in
QUILL Lite even though the work was mostly QUILL's side.

**L-221. Ctrl+Space takes the sentence**
- Do: put the cursor in the middle of a sentence and press **Ctrl+Space**.
- Pass: the whole sentence is selected and you hear "Selected sentence" with a
  word count. QUILL answers the same key the same way now; it used to select a
  "chunk" there.
- [ ] pass  [ ] fail: ______

**L-222. Nothing else moved in QUILL Lite**
- Do: read Edit ▸ Selection top to bottom.
- Pass: every key is the one it was. QUILL Lite's selection keys were already the
  family's; what changed was QUILL coming into line with them.
- [ ] pass  [ ] fail: ______

---

## Block R -- The 2026-09-18 additions (10 min)

The family parity program. Most of it landed on QUILL's side; these are the
QUILL Lite halves, and the two that are shared behave identically in both by
design -- so if one of these fails here, check QUILL before filing it as
QUILL Lite's.

### The File Encoding and Line Endings window

**L-223. It shows what this file actually is**
- Do: make a file whose lines end with a single CR (classic Mac); writing
  `b"one<CR>two<CR>"` as raw bytes is enough. Open it in QUILL Lite and press
  **Ctrl+Alt+E**.
- Pass: the Line Endings list starts on a row saying **keep as is**, naming CR.
- Fail if it reads "CRLF" or "LF". Until 2026-09-18 it read CRLF -- the list fell
  back to its first row for anything it could not offer, so the window stated a
  fact about the file that was not true.
- [ ] pass  [ ] fail: ______

**L-224. Confirming it does not convert a file you only opened**
- Do: with that same file open and the window showing **keep as is**, press
  **Enter** to confirm, then **Ctrl+S**.
- Pass: the file on disk still has single-CR line endings. Check the byte size,
  or reopen it -- the line count must not have changed.
- [ ] pass  [ ] fail: ______

**L-225. A UTF-16 big-endian file is still big-endian afterwards**
- Do: save a file as UTF-16 big-endian with a BOM (Notepad's "Unicode big
  endian" will do). Open it in QUILL Lite, change nothing, press **Ctrl+S**.
- Pass: the first two bytes are still `FE FF`.
- Fail if they are `FF FE` -- that is little-endian, every pair of bytes in the
  file swapped by a save that changed nothing else. Both byte orders used to
  decode through the one codec that always writes little-endian.
- [ ] pass  [ ] fail: ______

### The status bar in a rich document

**L-226. Encoding and Line Endings say a rich document has neither**
- Do: open or make a `.rtf`. Press **F6** and read the **Encoding** and **Line
  Endings** parts.
- Pass: **"RTF (rich text)"** and **"Not applicable (rich text)"**.
- Fail if they read "UTF-8" and "CRLF". Those are a plain file's two answers, and
  RTF has neither -- it writes an accented letter as an escape sequence of its
  own and marks a paragraph its own way. This is in the 15-minute pass for the
  same reason L-90 and L-121 are: a status cell that states a fact the document
  does not have is the defect this product cannot ship.
- [ ] pass  [ ] fail: ______

### The keys the editing control brings with it

**L-227. A formatting key that cannot mean anything says so**
- Do: in a **plain text** document, press **Ctrl+U**.
- Pass: nothing is underlined, and you hear **"Underline has no meaning in a
  plain text document."**
- Fail if the text underlines (the old behaviour: really applied, not marked
  dirty, never announced, never saved), or if the key is swallowed in silence.
- [ ] pass  [ ] fail: ______

**L-228. Said once, not on every press**
- Do: press **Ctrl+U** twice more in the same document.
- Pass: silence both times. A key that explains itself on every press is noise
  inside a minute.
- [ ] pass  [ ] fail: ______

**L-229. Each effect gets its own one explanation**
- Do: in the same document press **Ctrl+R**, then **Ctrl+R** again.
- Pass: **"Right alignment has no meaning in a plain text document."** the first
  time, silence the second. Once per effect, not once per document -- the second
  key is a different question.
- [ ] pass  [ ] fail: ______

**L-230. A Markdown document names itself, and so does an HTML one**
- Do: switch to Markdown (**Alt+Shift+F** until the Format part says so) and
  press **Ctrl+U**. Then switch to HTML and press **Ctrl+E**.
- Pass: **"... in a Markdown document."** and **"... in an HTML document."**
- Fail on **"a html document"**: QUILL Lite lower-cased its own Format label
  before building the sentence, so an initialism lost the article it needs when
  spoken aloud. Both editors now name a kind of document from one shared table.
- [ ] pass  [ ] fail: ______

**L-231. A rich text document still underlines**
- Do: switch to **Rich text** and press **Ctrl+U**, then type a word.
- Pass: the word is underlined and nothing is said about meaning. The guard is
  for documents that cannot hold formatting; in a rich one the control's own key
  is exactly right.
- [ ] pass  [ ] fail: ______

### Spelling

**L-232. Suggestions spell themselves as you arrow**
- Do: type `recieve`, open the spelling review (**F7**), and arrow down the
  suggestion list.
- Pass: each suggestion is said and then, after a pause, spelt out.
- Fail if you hear only the words. "receive" and "recieve" are the same sound,
  which is the whole reason the list exists; choosing between them by ear is
  impossible without the letters. Interruptible as always: press the next key and
  the spelling stops unheard.
- [ ] pass  [ ] fail: ______

### Word's last three keys

**L-233. F12, Ctrl+F12 and Ctrl+Shift+F12**
- Do: press **F12**. Escape. Press **Ctrl+F12**. Escape. Press
  **Ctrl+Shift+F12**.
- Pass: Save As, then Open, then Print -- Word's keys for all three. They are
  aliases: **Ctrl+Shift+S**, **Ctrl+O** and **Ctrl+P** still work.
- Fail if any of the three does nothing. QUILL carried all three and QUILL Lite
  carried none, which is a habit that works in one editor and not the other.
- [ ] pass  [ ] fail: ______

### After QUILL brings your setup across

Run these only if you have also run QUILL's **Bring My QUILL Lite Settings**
(**Alt+Shift+F11** there) on the same machine, and answered yes.

**L-234. QUILL Lite is reading the shared stores from QUILL**
- Do: in QUILL Lite, open its preferences and find the two sharing switches
  (abbreviations, personal dictionary).
- Pass: both are **on**. QUILL turned them on when it took the copies, because
  QUILL holding your words while QUILL Lite still reads its own copy is what makes
  a "shared" store look broken.
- [ ] pass  [ ] fail: ______

**L-235. A word added in one editor is there in the other**
- Do: in QUILL, add an abbreviation. Restart QUILL Lite and expand it.
- Pass: it expands. One set of abbreviations, both editors.
- [ ] pass  [ ] fail: ______

**L-236. Nothing of yours was replaced**
- Do: check an abbreviation you had in QUILL Lite before the merge, and one you
  had in QUILL.
- Pass: both are still there, with their own expansions. QUILL wins a collision
  and nothing already in QUILL is overwritten, but neither side loses an entry
  the other did not have.
- [ ] pass  [ ] fail: ______

---

## Block S -- Reopening last session (6 min)

It reopened everything without asking until 2026-09-19. Everything here is about
the answer being **partial** and about Forget being **safe**: those are the two
claims the window makes, and a listener cannot check either by looking.

Set this up once: open three `.txt` files, close QUILL Lite, then delete or rename
one of the three from outside the app.

**L-237. Three documents means you are asked**
- Do: launch QUILL Lite.
- Pass: a window titled **Reopen Last Session**, whose first line says "3
  documents from last time, 1 of which is no longer there."
- Fail if three windows simply appear, or if the missing one is not mentioned.
- [ ] pass  [ ] fail: ______

**L-238. The row for the missing file says so and cannot be ticked**
- Do: arrow to the row naming the file you deleted. Press **Space**.
- Pass: the row reads "(the file is no longer there)" and stays unticked.
- [ ] pass  [ ] fail: ______

**L-239. The answer can be partial**
- Do: untick one of the two that are still there. Press **Open Checked**.
- Pass: exactly one document opens, and you hear "Reopened all 1 document."
- Fail if both open. The whole point of the window is that "yes" and "no" are per
  document.
- [ ] pass  [ ] fail: ______

**L-240. Not Now changes nothing**
- Do: relaunch, and press **Escape** at the window.
- Pass: nothing opens, and you hear that the same documents are offered next time.
  Relaunch again: the same three are offered.
- [ ] pass  [ ] fail: ______

**L-241. Forget takes a row off the list and leaves the file alone**
- Do: at the window, tick the missing one, press **Forget Checked**, then **Not
  Now**. Relaunch.
- Pass: two documents are offered, not three. **Every file you started with is
  still on disk** -- check the folder.
- Fail if any file is missing. Nothing in this window may delete anything.
- [ ] pass  [ ] fail: ______

**L-242. Forgetting is saved even though nothing opened**
- Do: as L-241 -- the Forget was followed by Not Now.
- Pass: the forgotten row is still gone after the relaunch. A Forget that is not
  written is a Forget that did not happen.
- [ ] pass  [ ] fail: ______

**L-243. One or two documents still open without a question**
- Do: with two documents open, close QUILL Lite and relaunch.
- Pass: both open, no window. The chooser is for the cases where the answer is not
  obvious, and two files that are still there is not one of them.
- [ ] pass  [ ] fail: ______

**L-244. A missing file brings the window up on its own**
- Do: with two documents remembered, delete one from outside the app and relaunch.
- Pass: the window appears even though there are only two. This is the case the
  old silent behaviour hid completely: nothing opened, nothing was said, and that
  is indistinguishable from "it opened and I have not found it yet".
- [ ] pass  [ ] fail: ______

**L-245. The key opens the same window any time**
- Do: press **Alt+Shift+F12** (File > Reopen Last Session...).
- Pass: the same window. With nothing remembered it says so rather than opening
  empty.
- [ ] pass  [ ] fail: ______

**L-246. Never Ask Again says what it changed, and can be undone**
- Do: press **Never Ask Again**, then relaunch twice.
- Pass: you are told what changed, and last session reopens silently from then
  on with no window.
- Then press **Alt+Shift+F12** to open the window on purpose. **Never Ask
  Again** is now greyed out and **Ask Me Next Time** is live. Press **Ask Me
  Next Time**, then relaunch with three documents remembered.
- Pass: you are asked again. Fail if Ask Me Next Time is greyed too -- that is
  the window being opened without its current mode, and it leaves no way back.
- Fail if either button is *missing* rather than greyed: a control that
  disappears leaves somebody searching the window for it, where a disabled one
  announces itself as unavailable on arrival.
- [ ] pass  [ ] fail: ______

---

## Block T -- The 2026-09-21 additions (5 min)

The braille fix (#616/#813) is on by default, and it costs the control its
answer for the caret's line whenever the caret sits on a final empty line. A
window subclass supplies the right answer, and on 2026-09-21 that subclass
stopped being able to end the process when the message chain under it faults.
Both halves are invisible until you listen: one is a line number, the other is
your document.

Run this block with a screen reader speaking, and with **Braille selection
support** left at its default (on). If it has been turned off, turn it back on
and restart QUILL Lite -- the flag is set once, when the editor is built, so the
setting does nothing until the editor is rebuilt.

**L-247. The final empty line is blank**
- Do: in a new document, type `This is a test.` then press **Enter**. Do not
  type anything else.
- Pass: your reader says the new line is **blank** (JAWS "blank", NVDA "blank").
- Fail if it repeats `This is a test.` -- that is the control answering line 0
  for a caret that is on line 1, and it happens on every empty line at the end
  of every document.
- [ ] pass  [ ] fail: ______

**L-248. The reader agrees about which line you are on**
- Do: with the caret still on that empty line, ask your reader to say the
  current line (JAWS **Insert+Up**, NVDA **NVDA+Up**), then press **F6** and
  read **Position**.
- Pass: both say line **2**. The point is agreement: the status bar is wx
  counting, the reader is asking the window, and until the subclass existed
  those two disagreed.
- [ ] pass  [ ] fail: ______

**L-249. An empty line in the middle is unaffected**
- Do: type `alpha`, **Enter**, **Enter**, `beta`. Arrow up to the blank line
  between them.
- Pass: **blank**, on line 2. Interior blank lines were always answered
  correctly; this check is here so a regression in the correction cannot hide
  behind the one case it was written for.
- [ ] pass  [ ] fail: ______

**L-250. Opening and closing many documents does not end the app**
- Do: open and close ten documents in a row -- **Ctrl+O**, **Ctrl+W**, ten
  times -- typing a character into each before you close it. Then repeat
  L-247.
- Pass: QUILL Lite is still running, nothing was lost, and the final empty line
  is still blank. Each editor installs a subclass and each close takes one off;
  a mistake in that pairing does not misreport anything, it ends the process
  with whatever was unsaved in it.
- Fail loudly if the app disappears. Keep the crash report, and say how many
  documents in it happened.
- [ ] pass  [ ] fail: ______

**L-251. If the correction ever gives up, it gives up quietly**
- Do: nothing to trigger this -- read it so you recognise it. Should the
  message chain fault, QUILL Lite detaches from that one control and logs a
  warning naming the message number, rather than going down.
- Pass: the symptom to report is **one** editor that has started repeating the
  last line on its final empty line while the rest of the app behaves. That is
  the fallback working, and it is still a bug worth a report, with the log.
- [ ] pass  [ ] fail: ______

---

## Sign-off

| | |
| --- | --- |
| Build / version | |
| Date | |
| Screen reader and version | |
| Windows version | |
| Blocks run | |
| Tests failed (numbers) | |

**Verdict:** [ ] ship  [ ] ship with findings  [ ] do not ship

Findings worth carrying into the release notes:

```
```
