# QUILL Tutorials

23 guided tutorials, 136 steps, about 120 minutes of material in all.

This document is generated from the tutorials inside QUILL, so it says exactly what the app teaches. To work through one with the app watching -- running a step for you, and moving you on once it can see you have done it -- open **Help > Tutorials...** instead.

The keys below are the ones QUILL ships with. If you have rebound something in the Keyboard Manager, the tutorials *inside the app* say your key; this document cannot know it.

## Contents

- **Your first hour** -- Write and save something, learn the four ways of getting anywhere, meet the QUILL key, and learn what to press when you are lost.
  - Write and save your first document (5 minutes)
  - Get around a long document (6 minutes)
  - Do anything by name (4 minutes)
  - The QUILL key (5 minutes)
  - Getting unstuck (4 minutes)
- **Writing and editing** -- Selecting and moving text without a mouse, finding and replacing at every level of ambition, structure and formatting, words, and the one structure plain caret movement handles badly.
  - Select, mark, and move text (6 minutes)
  - Find, replace, and search across files (6 minutes)
  - Structure and formatting (6 minutes)
  - Spelling, words, and the thesaurus (5 minutes)
  - Tables, by ear (4 minutes)
- **Reading and reviewing** -- Having the document read to you, seeing the formatting that is normally hidden, single-letter movement, and inspecting a document somebody else wrote.
  - Have it read to you (6 minutes)
  - See the formatting that is normally hidden (6 minutes)
  - Quick Nav: single-letter movement (4 minutes)
  - Inspect a document you did not write (5 minutes)
- **How much QUILL says** -- Verbosity profiles, the channels that carry an announcement, and the echo of everything QUILL has just said.
  - Decide how much QUILL says (6 minutes)
- **The assistant, if you want one** -- Optional, explicit, and honest about what it did: setting up a provider or running on-device, asking a question, and the commands that work on one selection at a time.
  - Set up the assistant, or do not (6 minutes)
  - Ask, and run a prompt (6 minutes)
  - The assistant on one piece of text (4 minutes)
- **Living with it** -- Shaping the app to the work you actually do, the safety net underneath it, formats other people send you, braille files, and the family of apps QUILL sits in.
  - Make QUILL the size you need (6 minutes)
  - The safety net (5 minutes)
  - Open anything, save as anything (5 minutes)
  - Braille files, page by page (6 minutes)
  - QUILL and the apps around it (4 minutes)

## Your first hour

Write and save something, learn the four ways of getting anywhere, meet the QUILL key, and learn what to press when you are lost.

### Write and save your first document

New, type, save, and know where it went -- plus the two things QUILL does at startup that you should not be surprised by.

*6 steps, about 5 minutes.*

1. **Start where the app puts you.** There is no splash screen. The window appears with a menu bar, an editor and a status bar, and focus is in the editor. If QUILL detects a screen reader it adjusts its hints and its announcement style to match.
   - You should hear: Your screen reader announcing the editor.

2. **Make a document.** New opens an empty document in its own tab. QUILL is multi-document: every file you open lives in a notebook tab, and Ctrl+Tab moves between them.
   - Keys: Ctrl+N
   - You should hear: A new, empty document.

3. **Type a few lines.** Just write. QUILL's editor is plain text that is aware of Markdown and HTML when your document is one of those -- it does not impose a format on a file that has none.
   - You should hear: Your screen reader's own typing echo, and nothing from QUILL on top of it.

4. **Save it.** Save writes the file; Save As chooses the name and the format. If you prefer a smaller, screen-reader-friendly file picker, turn on Use simple file open dialog in Settings > General.
   - Keys: Ctrl+S
   - You should hear: The file saved, and its name.

5. **Ask where you are.** Press F6 to move into the status bar. It is a working surface rather than a strip of text: line and column, word count, insert or overwrite, selection size, encoding, line endings, spell state, background tasks, autosave timing, and the file path all live there, and each cell can be activated.
   - Keys: F6, Left arrow, Right arrow
   - You should hear: The cell you landed on, then each cell as you arrow across.
   - Worth knowing: Shift+F6 cycles back. The regions are Editor, the document tabs when they are shown, the preview when it is open, and the status bar.

6. **Know what QUILL does about a crash.** If QUILL notices an earlier crash or an autosave state, it offers recovery rather than silently hoping you forgot. And if your screen reader disappears mid-session, QUILL snapshots every open document to autosave first and then explains what happened through whatever can still speak.
   - You should hear: At the next launch: an offer to recover, naming what it found.

That is the whole loop: new, type, save. The rest of QUILL is about not having to hunt for anything.

Next: Get around a long document; Do anything by name.

### Get around a long document

Line, heading, structure, bookmark and history -- the movement that makes a two-hundred-page document feel small.

*7 steps, about 6 minutes.*

1. **Jump to a line.** Go to Line is the plainest jump and the one you will use when somebody quotes a line number at you. QUILL says where it landed rather than leaving you to check.
   - Keys: Ctrl+G
   - You should hear: The line number, and the line itself.

2. **Move by structure.** Next Structure and Previous Structure move by the document's own shape -- headings, blocks, regions -- rather than by characters. In a long document this is the difference between reading and searching.
   - Keys: Alt+Down
   - You should hear: The structure you landed on, named.

3. **Open the outline.** The Outline Navigator and the Heading Organizer give you the document's headings as a list you can move through and jump from -- and the organizer can reorder sections, not just visit them.
   - Keys: Ctrl+Shift+O
   - You should hear: The headings, with their levels.

4. **Drop a bookmark and come back.** Set a temporary bookmark before you go and look at something else, and go back to it when you are done. For places you return to often, named marks are worth learning.
   - Keys: Ctrl+J
   - You should hear: Bookmark set -- then, later, the line you left.

5. **Retrace your steps.** Back Location and Forward Location walk your movement history, the way a browser's back button does. It is the answer to where was I before I followed that link.
   - Keys: Alt+Left
   - You should hear: The place you came from.

6. **Ask where you are, at any time.** Speak Status Summary says where the cursor is and what state the document is in; Speak Full Path says which file you are actually in, which matters when two drafts have the same name.
   - Keys: Ctrl+Shift+Grave, Q
   - You should hear: Line, column, and the document's state, in one sentence.

7. **Move between documents.** Ctrl+Tab and Ctrl+Shift+Tab move between open documents, and Ctrl+W closes the one you are in. QUILL opens generated things -- the keyboard reference, a compare summary -- as ordinary tabs too, so artifacts stay close to the work that made them.
   - Keys: Ctrl+Tab
   - You should hear: The document you moved to, by name.

Structure, outline, bookmarks and history. Between them, you should never have to arrow through a document to find something again.

Next: Do anything by name.

### Do anything by name

The command palette, Go to Anything, and the keyboard reference that is generated from your own keymap rather than written down somewhere.

*5 steps, about 4 minutes.*

1. **Open the command palette.** Type what you want rather than remembering where it lives. The palette is the fastest route to anything QUILL can do, and it teaches you the key while you use it: every entry shows its own shortcut.
   - Keys: Ctrl+Shift+P
   - You should hear: A search box, then the commands as you narrow them.

2. **Learn what an unavailable command means.** When a command cannot run, the palette says why rather than showing a bare unavailable. A menu item disabled by a safety advisory carries the same reason in its help text.
   - You should hear: The reason, in a sentence.

3. **Go to anything.** Go to Anything is the other door: one box that reaches files, headings, symbols and places rather than commands. Use the palette when you want to *do* something and this when you want to *reach* something.
   - Keys: Ctrl+Shift+Grave, G
   - You should hear: A search box, then matches grouped by what they are.

4. **Read the keys you actually have.** The keyboard reference is generated from your current feature profile and your own keybindings, so it always describes the QUILL in front of you -- not the one in a manual written a year ago.
   - Keys: Ctrl+F1
   - You should hear: The reference, opening as an ordinary document tab.

5. **Find one key fast.** The key cheat sheet is the filtered version: type what you want to do and it narrows. It is the quickest way to answer what is the key for this without leaving what you are doing.
   - Keys: Alt+Shift+/
   - You should hear: A filter box, then the matching keys.

Palette to do, Go to Anything to reach, cheat sheet to remember. None of the three asks you to have memorised anything.

Next: The QUILL key.

### The QUILL key

One chord that opens most of QUILL's power features, and the browse mode that turns single letters into document navigation.

*5 steps, about 5 minutes.*

1. **Press it once, and listen.** The QUILL key is Ctrl+Shift+Grave -- the back-tick key above Tab. Pressed once it arms a short-lived prefix: the next key you press runs a chord command, and then the prefix expires. A short two-tone earcon confirms it armed, so you know before any speech arrives.
   - Keys: Ctrl+Shift+Grave
   - You should hear: A quick double-ping, unlike any other sound in the app.

2. **Run one chord.** With the prefix armed, press G for Go to Anything or R for Read Aloud. Menus and the cheat sheet write these as QUILL Key + G, which is the same thing said in words.
   - Keys: Ctrl+Shift+Grave, G
   - You should hear: Whatever that command announces.

3. **Ask the chord list.** QUILL Key + ? opens the full cheat sheet of chords. Every chord is data from the keymap, which means every chord is remappable in the Keymap Editor -- and the sheet shows what you have, not what shipped.
   - Keys: Ctrl+Shift+Grave, ?
   - You should hear: The chord list, filterable.

4. **Lock browse mode on.** Press the QUILL key twice and Quick Nav (browse) mode locks on: single letters move the cursor through the document's structure -- H for headings, P for paragraphs, S for sentences. Escape leaves.
   - Keys: Ctrl+Shift+Grave, Escape
   - You should hear: Browse mode on, then each structure as you move.

5. **Know why it is a chord and not a modifier.** A prefix chord costs one extra keystroke and buys a whole alphabet of commands that never collide with your screen reader's keys or the editor's. That trade is the reason it exists.
   - You should hear: Nothing: this is the design, not an action.
   - Worth knowing: On some keyboards Windows reports the grave key oddly, so QUILL detects it three independent ways -- by character, by virtual key, and by physical scan code.

Armed once for one command, pressed twice for a mode. Everything it reaches is also in the palette, so the chord is a shortcut rather than a requirement.

Next: Getting unstuck.

### Getting unstuck

F1, the echo of what QUILL just said, why a thing is unavailable, and the undo that covers more than typing.

*6 steps, about 4 minutes.*

1. **Ask what the thing under your cursor is.** F1 on any focusable control -- a field, a button, a menu item, the editor itself -- opens help that says what the control does and which keys apply to it, all in one read-only field so your reader announces it in one pass.
   - Keys: F1
   - You should hear: The window's purpose, then the control's own help.

2. **Ask what you can do here.** Shift+F1 answers What Can I Do Here for the document you are in, which is a different question from what is this control: it is about the work rather than the widget.
   - Keys: Shift+F1
   - You should hear: What this kind of document supports, in context.

3. **Re-read what QUILL just said.** Speech is fleeting: an indent depth, a save result, a no matches. The Spoken Echo remembers the last twenty things QUILL announced, newest first, in a dialog you can arrow through, review by character, select and copy.
   - Keys: Alt+Shift+E
   - You should hear: The last things QUILL said, as text.
   - Worth knowing: Double-pressing an informational command -- Describe Formatting, Document Summary, Context Help -- opens the Echo instead of repeating itself, the screen-reader convention. Alt+Shift+E always works.

4. **Find out why something is unavailable.** Why Unavailable answers for the command you were reaching for. QUILL's rule is that a refusal carries its reason -- in the palette, in a dimmed menu item's help text, and in error messages, which increasingly end with the concrete next step.
   - Keys: Alt+F1
   - You should hear: The reason, and what would change it.

5. **Take back the last thing.** Undo covers editing; Undo Last Action covers the destructive verbs elsewhere in the app. And every confirmation that would destroy something defaults to No, so pressing Enter reflexively can never cost you data.
   - Keys: Ctrl+Z
   - You should hear: What came back.

6. **Know the promise underneath.** Anything that closes or degrades QUILL without your asking persists your work first. That rule is why the screen-reader watchdog snapshots your documents before it explains itself, and it applies everywhere in the app.
   - You should hear: Nothing: this is the sentence to remember on a bad day.

F1 for here, Shift+F1 for this work, Alt+Shift+E for what was just said. Between them there is no state you can be in without a way out.

## Writing and editing

Selecting and moving text without a mouse, finding and replacing at every level of ambition, structure and formatting, words, and the one structure plain caret movement handles badly.

### Select, mark, and move text

Selection that grows by structure rather than by character, marks you can return to, and a clipboard with twelve slots instead of one.

*6 steps, about 6 minutes.*

1. **Grow a selection by meaning.** Expand Selection takes the next larger structure -- word, then sentence, then paragraph, then block. It is far more predictable by ear than holding Shift and counting, and Shrink Selection goes back.
   - Keys: Ctrl+Shift+Grave, J
   - You should hear: What is now selected, and how much of it.

2. **Select exactly one paragraph or block.** Select Paragraph and Select Block take the unit you mean in one keystroke. Say Selected reads back what you have, which is the check worth making before a destructive edit.
   - You should hear: The paragraph, then its size.

3. **Drop a mark and come back to it.** Set Mark remembers where you are; Exchange Point and Mark jumps between the mark and the cursor, which is how you select across a long distance without holding anything down. Named marks survive for as long as you want them.
   - Keys: Ctrl+Shift+M
   - You should hear: Mark set -- and, on the exchange, where you landed.

4. **Use more than one clipboard.** The copy tray has twelve slots. Copy to a numbered slot, paste from a numbered slot, or open the tray and search it. It is the answer to gathering five quotes from one document into another without a round trip each time.
   - Keys: Ctrl+Shift+Grave, X
   - You should hear: The tray, with what each slot holds.
   - Worth knowing: Clear All Tray Slots asks first and defaults to No, like every destructive question in QUILL.

5. **Paste something that came from the web.** Magic Paste and Paste HTML as Markdown clean up what the clipboard actually contains, rather than dropping styled soup into your document. Copy With Source does the reverse courtesy when you are the one quoting.
   - You should hear: What it pasted, and what it cleaned up.

6. **Tidy lines in place.** Quote Lines, Unquote Lines, Reverse Lines, Keep Unique Lines, Number Lines and Trim Blank Lines each do one obvious thing to the selection. They are the small tools that save an hour when a document arrives badly.
   - Keys: Ctrl+Shift+Q
   - You should hear: How many lines it changed.

Selection by structure, marks for distance, twelve clipboards. None of it needs a mouse and none of it needs you to count characters.

Next: Find, replace, and search across files.

### Find, replace, and search across files

The four levels: find here, find every match, replace with care, and search or replace across a folder of files.

*6 steps, about 6 minutes.*

1. **Find, and find again.** Find opens the search; Find Next and Find Previous walk the matches. QUILL keeps your search history, so a search you run often gets shorter every time.
   - Keys: Ctrl+F
   - You should hear: The match, with its line -- or a plain statement that there are none.

2. **See every match at once.** Find All Matches opens a summary rather than making you walk the document. It is the right tool when the question is how many and where rather than take me to the next one.
   - Keys: Ctrl+Shift+F3
   - You should hear: How many matches, and the list of them.

3. **Choose the kind of search.** Plain text, whole word, wildcard, or regular expression. The Regex Helper explains the syntax when you need it, which is the difference between a powerful search and one you are afraid of.
   - You should hear: The mode you chose, read back.

4. **Replace deliberately.** Replace steps through and asks; Replace All does not. Both say how many they changed, and Undo takes the whole operation back as one action rather than one edit at a time.
   - Keys: Ctrl+H
   - You should hear: Each replacement, or the count at the end.

5. **Search a whole folder.** Search in Files answers where did I write that when you cannot remember which document it was in. Replace in Files is its counterpart, and it is worth doing on a copy the first time you use it.
   - Keys: Ctrl+Shift+F
   - You should hear: The matches, grouped by file.

6. **Learn the one that is not a search.** Go to Anything reaches files, headings and places rather than text. When you know the *name* of the thing you want, it is faster than any search.
   - Keys: Ctrl+Shift+Grave, G
   - You should hear: Matches grouped by what they are.

Find for here, Find All for how many, Search in Files for which document. The regex helper is there when the pattern gets hard.

Next: Structure and formatting.

### Structure and formatting

Headings, lists, emphasis and sections -- and Describe Formatting, which tells you what is actually on the text under your cursor.

*7 steps, about 6 minutes.*

1. **Make a heading.** Heading 1 through Heading 6 set the level directly, and Increase and Decrease Heading Level move an existing one. Headings are what the outline, Quick Nav and the structure keys all navigate by, so they earn their keystroke twice.
   - Keys: Ctrl+Alt+2
   - You should hear: The heading level, and the line it applied to.

2. **Emphasise something.** Bold and Italic do what they say, in the document's own language: Markdown gets Markdown, HTML gets tags, rich text gets real formatting. Bold means bold -- QUILL speaks your document's format rather than imposing one.
   - Keys: Ctrl+B
   - You should hear: Bold on, and what it applied to.

3. **Ask what formatting is here.** Describe Formatting says what is actually on the text under the cursor. It is the one-shot answer to why does this line sound different, and double-pressing it opens the Spoken Echo so you can read the answer rather than catch it.
   - Keys: Ctrl+Shift+D
   - You should hear: Every attribute on the text, in one pass.

4. **Make a list, and nest it.** Toggle Bullet List and Toggle Numbered List convert the selection. On a Markdown list item, Tab and Shift+Tab nest and promote the item, and each move is spoken -- so you hear the indent even though the caret does not move.
   - Keys: Ctrl+Alt+B
   - You should hear: The list applied, then the new depth as you nest.

5. **Move a whole section.** Move Section Up and Move Section Down move a heading and everything under it. Reordering a document by its structure rather than by cut and paste is the difference between an edit and an afternoon.
   - Keys: Alt+Shift+Up
   - You should hear: Where the section moved to.

6. **Insert the awkward things.** Insert Link, Insert Table, Insert Snippet, Insert Emoji, Insert Special Character and Insert Equation each open a small, keyboard-first window rather than expecting you to type syntax from memory.
   - Keys: Ctrl+Alt+K
   - You should hear: The window, with focus in its first field.

7. **Decide what Tab does.** By default Tab indents the line and Shift+Tab outdents. If you would rather Tab typed a literal tab character, the Tab Mode chord switches it, the status bar shows which mode you are in, and Shift+Tab still outdents either way.
   - Keys: Ctrl+Shift+Grave, U
   - You should hear: The new mode, and afterwards the depth on every indent.

Structure first, emphasis second. Describe Formatting is the key to keep: it turns a guess into a fact.

Next: Spelling, words, and the thesaurus.

### Spelling, words, and the thesaurus

Spell check as a list rather than a march, the ranked view for a long document, word count, and the thesaurus.

*6 steps, about 5 minutes.*

1. **Check one word.** Spell Check Word at Cursor answers the question you actually have -- is this one right -- without starting a pass through the whole document.
   - Keys: Alt+F7
   - You should hear: The verdict, and suggestions if it is wrong.

2. **Get the misspellings as a list.** The misspelling list is a list you can arrow through and jump from, rather than a modal march through the document. For a long piece the ranked view puts the ones that occur most first, which is usually the same word thirty times.
   - Keys: Alt+Shift+L
   - You should hear: How many, then each one with its context.

3. **Walk them one at a time when you want to.** Next Misspelling and Previous Misspelling are the classic movement, and they exist alongside the list rather than instead of it. Use whichever suits the document.
   - Keys: Ctrl+F7
   - You should hear: The word, and the line it is on.

4. **Count what you have written.** Word Count reports the document or the selection. Document Summary is the bigger answer -- what this document is, how long, and how it is shaped.
   - Keys: Ctrl+Shift+W
   - You should hear: Words, characters, and the rest.

5. **Find a better word.** The thesaurus works on the word under the cursor and offers replacements you can apply straight into the document, rather than a list you have to copy out of.
   - Keys: Shift+F7
   - You should hear: The word, then its alternatives.

6. **Know what an AI check adds.** AI Spell Check and Check Grammar with AI are separate commands, and they never apply anything automatically: the grammar check lists corrections as original phrase, arrow, corrected phrase, and a reason, and you apply what you agree with.
   - Keys: Ctrl+Alt+Shift+G
   - You should hear: Each correction with its reason, and nothing changed yet.

The list before the march, the ranked list for a long document, and an AI pass only when you ask for one.

Next: Tables, by ear.

### Tables, by ear

The one structure plain caret movement handles badly, and the six keys that fix it.

*6 steps, about 4 minutes.*

1. **Understand the problem.** Arrowing along a line in a table tells you the characters and never the shape. You can read every word of a row and still not know which column you are in, which is why tables get their own movement.
   - You should hear: Nothing: this is why the next six steps exist.

2. **Move along a row.** Next Cell and Previous Cell move one cell along the row, and each landing says where you are before it says what is there: Row 2 of 6, column 3 of 5: Portland.
   - Keys: Ctrl+Alt+Right
   - You should hear: The position, then the contents.

3. **Move down a column.** Cell Below and Cell Above move down and up the column. Reading a column is how you compare values, and it is exactly what character movement cannot do.
   - Keys: Ctrl+Alt+Down
   - You should hear: The new row and column, then the cell.

4. **Jump to the edges.** Row Start and Row End go to the ends of the row; First Cell and Last Cell go to the ends of the whole table. Four keys for the four questions you actually ask.
   - Keys: Alt+Home
   - You should hear: The cell you landed on, with its position.

5. **Hear the difference between an edge and a wall.** No more cells at the end of a row, No more rows at the bottom of a column, and No more cells, end of table on the very last cell. That is the difference between this row stops here and the table stops here.
   - You should hear: One of those three sentences, rather than silence.
   - Worth knowing: An empty cell is announced as blank rather than by silence, and the keys are harmless outside a table: QUILL simply says Not in a table.

6. **Know that a Word table behaves the same.** A .docx table is brought in as a real table laid out as Markdown rows, so the same keys, positions and edges apply to a table you opened from Word as to one you typed. A cell containing a pipe character stays one cell.
   - You should hear: The same position announcements, in an imported document.

Six keys, and every landing says where you are. Tables stop being the thing you dread in somebody else's document.

## Reading and reviewing

Having the document read to you, seeing the formatting that is normally hidden, single-letter movement, and inspecting a document somebody else wrote.

### Have it read to you

Start, pause and stop Read Aloud, choose a voice worth listening to, and know which voices are on your machine and which are a download.

*6 steps, about 6 minutes.*

1. **Start reading.** Read Aloud starts from the cursor and pauses on the same key. It is a different thing from your screen reader: it reads the document as a document, at a pace you set, while your reader keeps doing its own job.
   - Keys: Ctrl+Shift+Grave, R
   - You should hear: The document, from where you were.

2. **Stop it.** Stop ends the pass rather than pausing it. Pause keeps your place, which is what you want when somebody speaks to you; Stop is what you want when you are done.
   - Keys: Ctrl+Shift+Grave, Shift+R
   - You should hear: Silence, and the status bar's read-aloud cell going quiet.

3. **Know which voices you already have.** The Windows system voice runs on SAPI 5 and is always there, offline, with no download -- it is the floor that keeps Read Aloud working immediately. DECtalk, eSpeak NG, Piper and Kokoro are explicit downloads, so a base install stays small.
   - You should hear: The voice list, with each engine named.

4. **Audition one before you commit.** Preview in Manage Voices synthesises the phrase with the real voice when it is installed, and plays a short pre-recorded sample when it is not -- so you can hear a neural voice before deciding to download 120 MB of it.
   - You should hear: The sample, and a note when it is a recording rather than the real thing.
   - Worth knowing: Rate, volume and pitch apply to real synthesis, so they stay dimmed until the voice is downloaded. Nothing pretends to work.

5. **Read a document that is not in English.** The Windows engine lists every voice installed on your PC in any language, and the Kokoro pack includes Spanish, French, Hindi, Italian and Brazilian Portuguese. Pick the voice whose language matches the document.
   - You should hear: The document, pronounced correctly rather than phonetically.

6. **Turn a document into audio.** The Audiobook and Batch Speech wizard converts a folder of documents to speech audio, or builds a chaptered audiobook. It asks one thing at a time -- what to read, who reads it, how chapters work, and where the output goes.
   - Keys: Ctrl+Shift+Grave, Y
   - You should hear: The wizard, one question per page.

The system voice is always there; everything else is an explicit choice you can audition first.

Next: See the formatting that is normally hidden.

### See the formatting that is normally hidden

Reveal Codes -- the WordPerfect feature rebuilt for a screen reader -- and the character inspector that tells a smart quote from a straight one.

*6 steps, about 6 minutes.*

1. **Open Reveal Codes.** A pane below the editor shows your document as an ordered stream of bracketed codes and text: Bold On, Font, Heading 2, Tab, Hard Return, No-Break Space. The editor itself does not change -- this is a window onto the scaffolding.
   - Keys: Alt+F3
   - You should hear: The pane, and the code or text at your position.

2. **Move between the two panes.** F6 cycles Editor, Reveal Codes, Status Bar, and the two carets stay in sync however you move -- arrows, word jumps, Home and End, or a jump from Find. Sit in whichever one you like; your place tracks along.
   - Keys: F6, Shift+F6
   - You should hear: The region you entered, then your position in it.

3. **Walk the codes.** Left and Right step over a whole code as a single unit -- one press crosses Bold On and your reader says bold on, never spelled out. An opening code also tells you how far its formatting reaches: bold on, 12 characters.
   - Keys: Left arrow, Right arrow, Ctrl+Left, Ctrl+Right
   - You should hear: Each code named as a unit, with its reach.

4. **Edit a formatted run in place.** Land on text between a pair of codes and press F2: the pane restricts you to that region, Enter applies your change and Escape cancels. The surrounding codes are left exactly as they were, and a nested code comes along with the run.
   - Keys: F2, Enter, Escape
   - You should hear: The region you are editing, then the change applied.

5. **Choose how it reads.** Flowed renders the codes inline within the running text and is the closest match to the classic view; Structured lists one item per code for scanning. Verbosity chooses quiet, balanced or detailed -- the last adds Unicode notes for invisibles.
   - You should hear: The view and verbosity you chose, remembered between sessions.

6. **Inspect a single character.** Describe Character at Cursor names what is actually under the cursor: a curly quote against a straight one, a no-break space, an invisible zero-width space that quietly breaks a search. It gives the name, the code point, the category and a note for the invisibles.
   - You should hear: The character's name, code point and category, in one pass.
   - Worth knowing: It ships without a shortcut; assign one in the Keymap Editor if you inspect text often. Search for Describe Character.

Reveal Codes costs nothing until you open it, and it is the answer to why does this line behave differently.

Next: Quick Nav: single-letter movement.

### Quick Nav: single-letter movement

Browse mode, where single letters move by structure -- the habit every screen-reader user already has from the web, brought into a text editor.

*5 steps, about 4 minutes.*

1. **Turn it on.** Press the QUILL key twice and Quick Nav locks on. This is the most common path: the first press arms the prefix, the second locks browse mode. It stays until Escape.
   - Keys: Ctrl+Shift+Grave
   - You should hear: Browse mode on.

2. **Move by heading.** H moves to the next heading, exactly as it does on a web page. That is the point of the whole mode: the movement you already know, in a document you are writing.
   - Keys: H
   - You should hear: The heading, with its level.

3. **Move by paragraph and sentence.** P moves by paragraph, S by sentence. Reading a draft this way -- sentence by sentence rather than line by line -- is how you hear a sentence that runs on.
   - Keys: P, S
   - You should hear: Each paragraph or sentence as you land on it.

4. **Leave.** Escape leaves browse mode and you are typing again. If you would rather the mode expired on its own, the sticky setting controls that -- and QUILL Key + N arms it for one action only.
   - Keys: Escape
   - You should hear: Browse mode off.

5. **Rebind what the letters do.** Quick Nav actions appear in the Keymap Editor as their own entries, so the letters are yours to change. Nothing in QUILL asks you to accept a key you would not have chosen.
   - You should hear: The editor, with the Quick Nav entries listed.

One mode, the letters you already know, and Escape to leave. It is the fastest way to read a long draft you wrote yourself.

Next: Inspect a document you did not write.

### Inspect a document you did not write

Summaries, folds, compare, and the report tabs that make somebody else's file readable rather than mysterious.

*5 steps, about 5 minutes.*

1. **Ask what this document is.** Document Summary is the one-shot answer: what it is, how long, and how it is shaped. It is the right first key on a file somebody has just sent you.
   - Keys: Alt+I
   - You should hear: The summary, in one pass.

2. **Collapse what you are not reading.** Toggle Fold collapses a section; List Folds shows what is folded; Next Fold and Previous Fold move between them. In a long structured document, folding is how you make the shape audible.
   - Keys: Ctrl+Alt+Shift+F
   - You should hear: Folded, and how many lines went away.

3. **Compare two versions.** The compare tools open their summary as an ordinary document tab -- artifacts stay close to the work that made them -- and Next Difference, Previous Difference and Announce Difference walk it by ear.
   - Keys: Ctrl+Alt+Shift+.
   - You should hear: Each difference, described rather than shown.

4. **Read the extraction report.** When QUILL brings text in from a PDF or a scanned document, the intake report says how it went -- what it was confident about and what it was not. Reading it is how you know whether to trust the text.
   - Keys: Ctrl+Shift+I
   - You should hear: The report, as an ordinary tab you can arrow through.

5. **Find the characters that do not belong.** The non-ASCII report lists what is unusual in the document, and jumping between the report and the source takes you straight to each one. It is how a stray byte-order mark or a curly quote stops being a mystery.
   - You should hear: The report, then each occurrence as you jump to it.

Summary first, folds for shape, compare for change, and the reports for what the file will not tell you itself.

## How much QUILL says

Verbosity profiles, the channels that carry an announcement, and the echo of everything QUILL has just said.

### Decide how much QUILL says

Verbosity profiles, the channels that carry an announcement, and the two settings that stop a burst of speech from burying you.

*7 steps, about 6 minutes.*

1. **Open verbosity preferences.** Find it in the command palette by typing verbosity. This is the window that decides how talkative QUILL is -- which is a different question from how talkative your screen reader is, and QUILL never duplicates what the reader already says.
   - Keys: Ctrl+Shift+P
   - You should hear: The verbosity window, with your current profile.

2. **Pick a talkativeness.** Beginner gives full context for every action; Normal is informative and is the default; Expert suppresses routine confirmations but never errors; Quiet turns speech and earcons off, leaving braille and the status bar.
   - You should hear: The profile you chose, announced as you switch.

3. **Choose what carries an announcement.** Speech, braille and sound can each be turned off. Visual -- the status bar -- is always on and cannot be turned off, so you never lose the on-screen record of what happened.
   - You should hear: Each channel as you set it.

4. **Go quiet for a meeting.** Quiet Mode silences speech and earcons; Meeting Mode quiets sound further. A Q or M indicator shows while one is on, the status bar keeps updating, and Undo Verbosity Change steps back the last change you made.
   - You should hear: Quiet mode on -- and then nothing, which is the point.

5. **Stop a burst from burying you.** Collapse repeated announcements (on by default) stops QUILL repeating itself when you hold a key at the end of a list. An optional announcement budget caps how many are spoken in five seconds. Both affect speech only: the status bar shows everything.
   - You should hear: One announcement instead of fifteen.

6. **Trim two specific cues.** Announce entering and leaving dialogs is off by default, because your screen reader already announces dialogs and reads their titles. Announce indentation depth on Tab is on, because 4 spaces is more useful than Indented lines.
   - You should hear: The setting read back.

7. **Read what it just said.** The Spoken Echo remembers the last twenty announcements as text you can arrow through and copy. It records only what QUILL speaks -- never your typing -- and it is the answer to an announcement that went past while you were thinking.
   - Keys: Alt+Shift+E
   - You should hear: The recent announcements, newest first.

QUILL speaks alongside your screen reader rather than instead of it. Every setting here is about how much of its own voice you want.

Next: Make QUILL the size you need.

## The assistant, if you want one

Optional, explicit, and honest about what it did: setting up a provider or running on-device, asking a question, and the commands that work on one selection at a time.

### Set up the assistant, or do not

On-device or a provider, where the keys live, and the honesty rules the assistant follows about what it did with your text.

*6 steps, about 6 minutes.*

1. **Know that it is optional.** QUILL includes an assistant; it does not require one. It runs on-device with a local model, or connects to a provider you choose explicitly -- Ollama, OpenAI, Claude, OpenRouter, Gemini, or a custom endpoint. Nothing is configured for you.
   - You should hear: Nothing: this is the fact that makes the rest optional.

2. **Open the AI Hub.** One window for every provider's key, model and test chat, plus per-provider key removal. It replaced two separate menu items, because a key and the model it unlocks are one subject.
   - You should hear: The Hub, with each provider and whether it is configured.

3. **Start with the one that needs no key.** Ollama needs no key at all: install it, run it, and QUILL detects it on localhost. It is the shortest path to a working assistant that sends nothing anywhere.
   - You should hear: Ollama detected, and the models it holds.

4. **Know where a key is kept.** In the Windows Credential Manager, tied to your Windows account -- or, in portable mode, in a DPAPI-encrypted file beside your data. Never in a settings file, never in a log, never in a diagnostic bundle, and never in QUILL's own program files.
   - You should hear: Nothing: this is the promise behind the field.

5. **Test it before you rely on it.** Test Chat in the Hub proves the key and the model work together. Doing that once, deliberately, is better than finding out in the middle of a document.
   - You should hear: The model's reply, in the Hub.

6. **Know the honesty rules.** If your document had to be trimmed to fit the model, QUILL says how much of it the answer used. If your provider was unreachable and the chat started on the on-device model instead, it says so the moment the chat opens. And it never switches to a cloud engine without telling you that is what a switch would mean.
   - You should hear: The sentence naming which engine answered, and on how much of the document.

Optional, explicit, and honest about what it did. If you never open the Hub, QUILL is a text editor and nothing else.

Next: Ask, and run a prompt.

### Ask, and run a prompt

The writing assistant, the one-shot question, and the prompt library -- including how to change what a built-in prompt actually says.

*6 steps, about 6 minutes.*

1. **Ask a question.** The writing assistant is a message-style window where you can ask, draft, propose edits and run QUILL commands -- with your approval before any change is applied. The provider and model in use are shown, and can be switched in the window.
   - Keys: Alt+Q
   - You should hear: The assistant, with focus in the prompt field when a model is configured.

2. **Send, and read the answer.** Ctrl+Enter sends. QUILL announces Sending and disables the button while the request is in flight, so a slow model is never mistaken for a dead one. The response opens read-only, with Copy to Clipboard.
   - Keys: Ctrl+Enter
   - You should hear: Sending, then the reply as reviewable text.

3. **Open the prompt library.** A searchable list of prompts on the left, the selected prompt's instruction on the right, and an optional input field. With the field blank it uses your selection, or the whole document.
   - You should hear: The prompts, filtered as you type.

4. **Run one on a selection.** Select a paragraph, choose Summarize or Improve Clarity or Make Concise, and run it. Nothing is applied automatically -- the result opens as a response you read and decide about.
   - You should hear: The result, in the response window.

5. **Change what a built-in prompt says.** Every built-in can have its wording overridden or be disabled, though built-ins cannot be deleted. Edit Check Grammar's text and the Check Grammar command picks up your version automatically.
   - You should hear: The prompt saved under your wording.

6. **Check grammar without being rewritten.** Check Grammar with AI lists corrections as original phrase, arrow, corrected phrase, and a reason. It does not rewrite the passage and it applies nothing: you make the changes you agree with.
   - Keys: Ctrl+Alt+Shift+G
   - You should hear: Each correction with its reason, and your document untouched.

Ask for a question, the library for a job you do often, and neither one changes your document without you.

Next: The assistant on one piece of text.

### The assistant on one piece of text

Translate, thesaurus, describe an image, and the spell check that asks a model -- each on the thing you have selected.

*5 steps, about 4 minutes.*

1. **Translate a selection.** Translate Selection works on what you have highlighted, so you can bring one paragraph across without sending a whole document anywhere.
   - Keys: Ctrl+Alt+Shift+T
   - You should hear: The translation, as a response you can copy.

2. **Ask for a better word.** The AI thesaurus is the other half of the offline one: it answers with alternatives in the sentence's own context rather than a dictionary list.
   - Keys: Ctrl+Alt+Shift+H
   - You should hear: The alternatives, with the sense each fits.

3. **Describe an image.** Describe Image is the command that matters most in somebody else's document. It answers what a picture is, which is the one thing a screen reader cannot do for you.
   - Keys: Ctrl+Shift+Grave, I
   - You should hear: The description, as text you can review and copy.

4. **Run an AI spell check.** AI Spell Check and its interactive form are separate from the ordinary dictionary check, because they answer a different question: not is this word in a list, but is this the word you meant.
   - Keys: Ctrl+Alt+Shift+I
   - You should hear: Each finding, one at a time.

5. **Switch engines deliberately.** Switch AI Engine changes which model answers. QUILL will offer a switch when a call fails and the other kind of engine could take it -- and it never makes that switch for you, always saying when one would send your text to the cloud.
   - Keys: Ctrl+Alt+Shift+E
   - You should hear: Which engine is now answering.

Every one of these works on a selection, which is the honest unit: you decide how much text leaves the paragraph you are in.

## Living with it

Shaping the app to the work you actually do, the safety net underneath it, formats other people send you, braille files, and the family of apps QUILL sits in.

### Make QUILL the size you need

Feature profiles, per-feature control, keyboard packs, and the keymap editor that tells you what a key is already doing.

*7 steps, about 6 minutes.*

1. **Understand what a profile is.** A profile decides which feature clusters are on, quiet or off. It keeps QUILL calm for somebody new without stripping power from somebody advanced -- and it is a starting point rather than a cage.
   - You should hear: The profile you are on, and what it covers.

2. **Pick the one that matches your work.** Essential is the calmest possible editor. Writer, Author or Student, Reader and Student, Office and Admin, Developer and Power Text, Low Vision, Braille and Screen Reader Power User, Accessibility Professional, and Full Quill each surface a different set.
   - You should hear: Each profile with a plain-English preview of what you get.

3. **Switch profiles from anywhere.** Quick-switch is one chord away, and Undo the last profile change is there when a switch was not what you wanted. You can compare two profiles before choosing.
   - Keys: Alt+Shift+P
   - You should hear: The profile you switched to.

4. **Turn one feature on without changing profile.** Manage Individual Features is per-feature control on top of your profile. Its Disabled features only view is the useful one: scan what is off and switch on the two things you actually miss.
   - You should hear: Each feature with a description of what it does and what it depends on.
   - Worth knowing: Enabling a feature enables its dependencies; disabling one turns off what depends on it, and QUILL says what changed.

5. **Start from a keyboard you already know.** Keyboard packs make QUILL feel familiar from day one: Quill Default, Writer, Navigation and Review, plus Windows Notepad, Notepad++, VS Code and Microsoft Word. Hand-edit anything afterwards and the label becomes Custom.
   - You should hear: The pack you chose, applied.

6. **Ask what a key is already doing.** In the Keymap Editor, type a *shortcut* rather than a command name and it flips to reverse lookup: it tells you which command owns that key, or that it is unassigned and available. You never have to guess whether a key is free.
   - You should hear: The command that owns the key, by its friendly title.

7. **Let it check itself.** Run Diagnostics audits the whole keymap -- duplicates, bindings for commands that no longer exist, unreadable bindings, keys that are assigned but inert -- and offers to heal the repairable ones in one step.
   - You should hear: What it found, and what it can fix.

A profile for the shape, individual features for the exceptions, a pack for the keyboard, and diagnostics when it all gets away from you.

Next: The safety net.

### The safety net

What QUILL does about crashes, autosave, a screen reader that vanishes, and every question that could destroy something.

*6 steps, about 5 minutes.*

1. **Know the rule.** Anything that closes or degrades QUILL without your asking persists your work first. Everything in this lesson is that one rule, applied in different places.
   - You should hear: Nothing: this is the sentence the rest follows from.

2. **Recover after a crash.** If QUILL notices an earlier crash or an autosave state, the next launch offers recovery rather than hoping you forgot. The autosave cell in the status bar tells you when the last one happened.
   - Keys: F6
   - You should hear: The autosave cell, with its timing.

3. **Know what happens if your screen reader stops.** QUILL watches the reader it detected at startup. One missed check is ignored -- restarting JAWS or NVDA must never set off alarms -- but a confirmed disappearance makes QUILL snapshot every open document to autosave and then explain through whatever can still speak.
   - You should hear: The explanation, through another reader or QUILL's own voice.
   - Worth knowing: QUILL does not shut down when this happens. Restart your reader when you are ready; QUILL announces when it sees it again, and the event is in Notifications either way.

4. **Trust the default answer.** Every confirmation that would destroy something has No as its default button, and a build check keeps it that way for every future dialog. Pressing Enter reflexively can never cost you data.
   - You should hear: The question, with No as the default.

5. **Go back to an earlier version.** Restore Previous Version brings back an earlier save of the document you are in. It is the one to remember when a well-meant edit went wrong two hours ago.
   - You should hear: The versions available, with their times.

6. **Read an error properly.** Messages carrying a support code end with the concrete next step -- install this, check that setting, switch to a local model. The code identifies the exact failure branch, so include it when you report a problem.
   - You should hear: The failure, the reason, and what to do about it.

Autosave, recovery, a watchdog on your screen reader, and No as the default answer. None of it asks you to be careful.

Next: Open anything, save as anything.

### Open anything, save as anything

One editor for every format, what QUILL does about a document it had to extract, and converting a file without hunting for a converter.

*5 steps, about 5 minutes.*

1. **Open what somebody sent you.** Every document opens in the one QUILL editor -- the same control, whatever the format. The rule to hold onto is that bold means bold: QUILL speaks your document's own language rather than flattening it.
   - Keys: Ctrl+O
   - You should hear: The document, and what kind it is.

2. **Save it as something else.** Save As chooses the format as well as the name: Markdown, HTML, Word, plain text and the rest. A document is not locked into the format it arrived in.
   - Keys: Ctrl+Shift+S
   - You should hear: The format list, then the file written.

3. **Convert without opening.** Convert File takes a source and an output format directly, which is the right shape when you have twenty files or when you do not want to read the thing at all. Batch Conversion does a folder.
   - Keys: Ctrl+Shift+Grave, B
   - You should hear: What it converted, and where it put the result.

4. **Check what the extraction actually got.** When text has been extracted -- from a PDF, from a scan -- the intake report says how it went. Reading it is how you decide whether to trust what you are reading, which is a question a sighted reader answers by glancing at the page.
   - Keys: Ctrl+Shift+I
   - You should hear: The report, as an ordinary tab.

5. **Switch the document's own format.** Switch Document Format changes how QUILL treats what is already open -- so a plain-text file you have decided is Markdown starts behaving like Markdown, headings and all.
   - Keys: Ctrl+Shift+Grave, K
   - You should hear: The new format, and the structure it now sees.

One editor, every format, and a report whenever the text had to be extracted rather than read.

Next: Braille files, page by page.

### Braille files, page by page

Opening a BRF as braille rather than as text, moving by braille page and cell, proofing without touching the file, and translating when the pack is installed.

*7 steps, about 6 minutes.*

1. **Open a braille file.** QUILL opens .brf, .brl, .pef and .ueb as plain braille ASCII -- nothing is transformed on the way in. The point is to let a proofreader move through a transcription the way it is actually laid out, in pages and cells.
   - Keys: Ctrl+O
   - You should hear: BRF file opened, 87 braille pages detected -- and your last position.

2. **Read the braille status cell.** While a braille file is active the status bar carries a braille cell: BRF Pg 12/87, Ln 14/25, Cell 31/40, Print 7. That is the braille page, the line within it, the cell within the line, and the print page.
   - Keys: F6
   - You should hear: The whole cell, read as one line.

3. **Move by braille page.** The Braille menu holds Go to Braille Page, Next and Previous Braille Page, and the same three for print pages. Stepping past the first or last says so rather than doing nothing.
   - You should hear: The page you landed on, with its number.
   - Worth knowing: Braille bindings ship deliberately unset so nothing collides with your screen reader; assign your own, or run them from the command palette.

4. **Proof without changing the file.** Mark the current page Proofed or Needs Review, add a note, list either set, and export a proofing report. Progress is kept in a small companion file beside the braille file, which is never modified.
   - You should hear: The page marked, and how far through you are.

5. **Validate the layout.** Validate BRF Layout scans for ten kinds of problem -- lines or pages too long, missing page breaks, mixed line endings, characters that are not braille ASCII, malformed page indicators -- and opens a warnings list you can step through.
   - You should hear: Warning 3 of 11, and what it says.

6. **Repair the two that stop it embossing.** Read Layout Metrics speaks the diagnostic numbers in one pass; Go to Longest Line and Go to Longest Page take you to the worst offender; and Remove Trailing Spaces clears the cause of most page-width problems while keeping every line ending and form feed intact.
   - You should hear: The metrics, then the line or page that broke the limit.

7. **Translate, when the pack is installed.** Back-Translate with Auto-Detect Code is the magical path: QUILL scores the document through every candidate code and says what it found -- Detected UEB Grade 2 (contracted) -- so you learn what your file is instead of being asked.
   - You should hear: The code it detected, then the draft it opened.
   - Worth knowing: Back-translation always opens as a clearly labelled draft, because no automatic back-translation is authoritative. The Translation submenu is hidden entirely when the pack is not installed, so you never meet a disabled item.

Byte-for-byte on save, a companion file for your progress, and a detector that tells you what code your file is in.

Next: QUILL and the apps around it.

### QUILL and the apps around it

The radio, the podcasts, the weather and the rest -- what lives inside QUILL, what is its own app, and what they share.

*5 steps, about 4 minutes.*

1. **Play the radio without leaving.** QUILL carries the same radio code Quill Radio does: browse stations, favorites, recording and scheduling, all from inside the editor. Your favorites are the same favorites in both.
   - You should hear: The browse tree, in QUILL.

2. **Know what has its own app, and why.** Quill Radio, QUILL Cast, Quill Weather and the rest exist so somebody who wants a radio does not have to install an editor. They share one data store, so nothing you set up in one is stranded from the others.
   - You should hear: Nothing: this is the shape of the family.

3. **Reach the weather.** Weather Now and Quick Weather are here as well, backed by the same code the standalone app runs. The alert watch, though, belongs to Quill Weather -- an app whose whole job is to keep running.
   - You should hear: The one-line summary for your primary place.

4. **Carry your place between them.** Your position in an episode, your bookmarks and your favorites are shared on this computer. Pause an episode in QUILL and open it in Cast and it picks up where you left off -- the later decision wins, not the furthest through.
   - You should hear: Picking up where you left off, and the time.

5. **Take your setup with you.** Export My Setup writes one file with your settings, keys and arrangement; Import My Setup puts them on another machine. Passwords stay behind, and the confirmation says so before it writes anything.
   - You should hear: What the file holds, named, before anything is written.

One editor that can do everything, and four small apps for the days you want one thing. They share their data and never fight over it.
