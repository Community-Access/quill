# QuillLite -- sign-off checklist

One pass, top to bottom, ticking boxes. Every step says exactly what to press,
exactly what to type, and the one thing that decides pass or fail.

The narrative version of every feature below is
[the user guide](../../standalone/quilllite/docs/userguide.md); the reasoning is
in [the PRD](../../standalone/quilllite/docs/prd.md) and
[the release notes](../../standalone/quilllite/docs/release-notes-1.0.md).

**Why this file exists.** Everything an automated test can answer about
QuillLite is already answered: 81 unit tests over the wx-free cores, the F1
audit, the access-key and over-announce gates, and 24 live checks against a real
`RICHEDIT50W` (`standalone/quilllite/tests/probe_live.py`). What none of them can
answer is what a person actually *hears*. That is this list.

## Before you start (3 minutes)

- Install or launch the build under test. Note the version from
  **Help > About QuillLite**: `____________`
- Have a screen reader running and speaking (JAWS or NVDA). Note which, and its
  version: `____________`
- QuillLite keeps everything in `%LOCALAPPDATA%\QuillLite`, separate from
  QUILL's `%APPDATA%\Quill`. For a clean run, rename that folder first; to keep
  your real one, take a copy.
- **Fail means:** it did not happen, or it happened silently, or what you heard
  differs from what this file quotes. Write down what you actually heard --
  "nothing" and "the wrong thing" are different bugs.
- Have three files to hand: a `.txt` saved with Windows line endings, a `.txt`
  saved with Unix line endings (any file from a git checkout will do), and any
  `.rtf`.

## The 15-minute pass

No time for the whole thing? Run exactly these twelve and stop:
**L-02, L-05, L-09, L-14, L-21, L-30, L-38, L-46, L-54, L-61, L-90, L-105.**

They cover the four things most likely to be wrong and worst if they are: the
document announces itself, F1 answers, the status bar is reachable, and a file
comes back byte-for-byte. L-90 is there because a status cell that misreports
what typing is about to do is the one defect this product cannot ship, and it
was shipped once already. **L-105** joined it on 2026-09-10 for the same reason
in reverse: a status bar that reads its own text back truncated is a cell
quietly lying about a fact, and the only place it shows is a narrow window on
the machine it was reported from.

---

## Block A -- Opening, and where focus lands (5 min)

**L-01. The window announces itself as a document**
- Do: launch QuillLite with nothing open.
- Pass: you hear a window title containing **"1: Untitled - QuillLite (plain
  text)"**. The number leads.
- [ ] pass  [ ] fail: ______

**L-02. Focus starts in the document**
- Do: launch QuillLite, do not touch anything, type `hello`.
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

**L-05. Alt+Tab shows QuillLite once, and the Window menu shows both**
- Do: press **Alt+Tab**, then come back. Open the **Window** menu (Alt+W).
- Pass: Alt+Tab lists QuillLite **once** (this is expected -- documents are
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
- Do: press **Ctrl+Shift+M** to switch to rich text (answer **Yes** if asked),
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
- Do: in a plain document with text in it, press **Ctrl+Shift+M** twice (to
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
  QuillLite document press **Ctrl+V**, then undo, then **Ctrl+Shift+V**.
- Pass: Ctrl+V brings the formatting; Ctrl+Shift+V brings the words only, and
  says how many characters.
- [ ] pass  [ ] fail: ______

**L-49. The copy tray remembers across a restart**
- Do: select text, **Ctrl+Alt+Y**. Close QuillLite entirely. Reopen. Press
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
- Do: type several paragraphs into a new document. Do **not** save. Wait 70
  seconds (the copy is taken once a minute). Kill QuillLite from Task Manager.
  Reopen it.
- Pass: the text is back, in its own window, marked unsaved, and you hear
  **"Recovered unsaved work from the last session"**.
- [ ] pass  [ ] fail: ______

**L-53. Saving clears the recovery copy**
- Do: save that recovered document, close QuillLite normally, reopen.
- Pass: nothing is offered back. `%LOCALAPPDATA%\QuillLite\recovery` is empty.
- [ ] pass  [ ] fail: ______

**L-54. Last session's documents reopen**
- Do: open two saved files. Close QuillLite with **Ctrl+Q**. Reopen.
- Pass: both are back, numbered in the same order.
- [ ] pass  [ ] fail: ______

**L-55. Naming a file on the command line wins over the session**
- Do: close QuillLite. Open a `.txt` from Explorer.
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
  QuillLite repeat a window title or control name your reader has just said.
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

**L-70. QuillLite does not create a QUILL data folder**
- Do: on a machine (or profile) with no QUILL installed, run QuillLite, save a
  file, quit.
- Pass: `%APPDATA%\Quill` does **not** exist. Only `%LOCALAPPDATA%\QuillLite`.
- [ ] pass  [ ] fail: ______

**L-71. Uninstalling leaves your work alone**
- Do: uninstall QuillLite.
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

**L-74. Shift+F7 handles the single word**
- Do: put the cursor inside a misspelled word and press **Shift+F7**.
- Pass: a suggestions list opens named for the word, Enter replaces it, and you
  hear **"Replaced with ..."**.
- [ ] pass  [ ] fail: ______

**L-75. Ctrl+F7 selects the misspelling, not just the position**
- Do: from the top of the document, press **Ctrl+F7**.
- Pass: the reader reads the misspelled word because it is *selected*. Landing
  beside it silently is a fail -- there would be nothing to hear.
- [ ] pass  [ ] fail: ______

**L-76. Alt+F7 teaches a word, and says where it went**
- Do: on a misspelling, press **Alt+F7**, then **Ctrl+F7** from the top again.
- Pass: you hear **"Added ... to your QuillLite dictionary"** -- naming *which*
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
- Pass: the cell has changed. QuillLite does not claim the Insert key -- the
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
  **no** `QuillLite` folder has appeared in `%LOCALAPPDATA%` on that machine.
- This is the one step worth running on a computer that has never had QuillLite
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
  and QuillLite never binds it. **Not** a beep, and **not** silence.
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
- Do: **Ctrl+Alt+Shift+F**. Type `curly quotes`. Then clear the box, choose the
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
- Do: make the window narrow -- narrow enough that twelve cells cannot fit on
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
- Do: **Ctrl+Alt+Shift+F**, and untick **The Command Palette**. Save. Press
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
- Do: with "Look for updates when QuillLite starts" ticked in Settings, close
  QuillLite and open it again. Then unplug the network and open it again.
- Pass: nothing is said either time -- no "checking", no "up to date", no
  network error. A launch is not the place to report that nothing happened.
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
