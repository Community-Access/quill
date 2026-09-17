# QuillLite Tutorials

8 guided tutorials, 33 steps, about 36 minutes of material in all.

This document is generated from the tutorials inside QuillLite, so it says exactly what the app teaches. To work through one with the app watching -- running a step for you, and moving you on once it can see you have done it -- open **Help > Tutorials... (Ctrl+Alt+F1)** instead.

The keys below are the ones QuillLite ships with. If you have rebound something in the Keyboard Manager, the tutorials *inside the app* say your key; this document cannot know it.

## Contents

- **Your first documents** -- Open a file and give it back unchanged, learn where the facts about it live, learn what kind of document you are in, and find your way between the ones you have open.
  - Open a file, and give it back unchanged (5 minutes)
  - Four kinds of document, and how to say which (4 minutes)
  - Your documents are numbered (3 minutes)
  - What to press when you are lost (3 minutes)
- **Working in a document** -- Selecting more than a few words, finding your way back to where you were, skimming something long, and spelling without a red squiggle.
  - Selecting more than a few words (6 minutes)
  - Finding your way back (5 minutes)
  - Skimming something long (5 minutes)
  - Spelling, without a red squiggle (5 minutes)

## Your first documents

Open a file and give it back unchanged, learn where the facts about it live, learn what kind of document you are in, and find your way between the ones you have open.

### Open a file, and give it back unchanged

The one promise QuillLite makes, and the three things it remembers about your file in order to keep it.

*4 steps, about 5 minutes.*

1. **Open something you already have.** Any text file will do, and an old one is a better test than a new one. QuillLite reads plain text, Markdown, HTML and rich text.
   - Keys: Ctrl+O
   - You should hear: The file's name, and the first line of it.

2. **Look at what it remembered.** The status bar is a row of cells you can arrow along, not a strip of text. Three of them are the promise: Encoding is how the letters are stored, Line Endings is how the lines finish, and Format is what kind of document this is. QuillLite puts all three back exactly as it found them.
   - Keys: F6
   - You should hear: Each cell's name and its value as you arrow along.
   - Worth knowing: Escape brings you back to your document. Nothing you do in the status bar changes the file unless you press Enter on a cell and answer the question it asks.

3. **Save it without changing anything.** Save it straight back. Then compare it with the original, however you like to do that -- it is the same file, byte for byte.
   - Keys: Ctrl+S
   - You should hear: "Saved" and the file's name.

4. **Type a character the file cannot hold.** If your file is stored in an older encoding, type an em dash or an emoji into it and save again. QuillLite asks before it writes: save as UTF-8 and keep it, save as asked and lose it knowingly, or cancel.
   - You should hear: A question counting the characters, naming the encoding, and offering Yes, No and Cancel.
   - Worth knowing: Before version 1.0 those characters became question marks and the app said "Saved". The only way to find out was to read that line again.

That is the product in four steps. Everything else is convenience on top of a file that comes back the way you left it.

Next: Four kinds of document, and how to say which.

### Four kinds of document, and how to say which

Plain text, Markdown, HTML and rich text -- what each changes, and the one key that rings between them.

*4 steps, about 4 minutes.*

1. **Find out what you are in.** The Format cell says which of the four this document is, and the Language cell says which markup a plain one is written in. QuillLite guesses from the file's name, and the guess is only ever a first guess.
   - Keys: F6
   - You should hear: The Format cell, reading "Markdown", "HTML", "Plain text" or "Rich text".

2. **Ring through the four.** One key walks all four, announcing each stop. Press it until you hear the one you meant. Moving between plain, Markdown and HTML changes nothing in your document -- it changes what the formatting keys write from now on.
   - Keys: Alt+Shift+F
   - You should hear: Each kind naming itself as you land on it.

3. **Go into rich text, and come back.** Rich text is the one stop that really converts. Going in turns Markdown into real formatting; coming out turns the formatting back into Markdown, and asks first, naming anything it cannot carry.
   - You should hear: A question before it converts, then "Rich text mode" or "Plain text mode".
   - Worth knowing: Your file keeps its name. Because a rich document cannot be written over a .txt, the next Ctrl+S offers you the right suffix already filled in.

4. **Say otherwise, for this window only.** Writing HTML in a scratch .txt is a reasonable thing to do. Document Language goes straight to one and tells you what each choice will do before you make it. The choice lasts as long as the window.
   - Keys: Ctrl+Alt+F6
   - You should hear: Each option described, and the one the file name would have chosen marked.

Next: Your documents are numbered.

### Your documents are numbered

Why there are no tabs, what you get instead, and the four ways to reach the document you want.

*3 steps, about 3 minutes.*

1. **Open a second file.** It opens inside the same window, as document 2. "Document 3" is a name you can hold in your head and say out loud; "the other Untitled" is not.
   - Keys: Ctrl+O
   - You should hear: The new document's number and name, in its title.

2. **Walk between them.** Ctrl+Tab is what most people press and Ctrl+F6 is what Windows documents. Both work, and so does the Window menu.
   - Keys: Ctrl+Tab
   - You should hear: The document you arrive at, announcing its number and name.

3. **Go straight to one.** Alt and a digit goes directly to that document. This is the fast way once you have more than two open, and it is the reason they are numbered at all.
   - Keys: Alt+1, Alt+2, Alt+3
   - You should hear: The document you asked for.
   - Worth knowing: Documents here are children of one window, so they do not appear in Alt+Tab. That is the cost of the numbering, and these four routes are how QuillLite carries it.

### What to press when you are lost

Three keys that answer where you are, what this does, and what exists.

*3 steps, about 3 minutes.*

1. **Ask what you are standing on.** F1 answers everywhere -- in the document, on a button, in any window. It says what the window is for and then what the control you are on does.
   - Keys: F1
   - You should hear: The window's purpose, then the control's.

2. **Ask what the facts are.** The status bar holds everything QuillLite knows about your document, and every message it has said. A message you missed is still in the first cell.
   - Keys: F6
   - You should hear: The last thing QuillLite said, and then each fact as you arrow.

3. **Ask what exists.** The Keyboard Shortcuts window lists every key QuillLite has, built from the live command table -- so it shows your keys, including any you have changed.
   - Keys: Ctrl+F1
   - You should hear: A searchable list of every command and its key.

Nothing in QuillLite is more than these three keys away from being explained.

## Working in a document

Selecting more than a few words, finding your way back to where you were, skimming something long, and spelling without a red squiggle.

### Selecting more than a few words

Three genuinely different answers to the same problem, and when each one is the right one.

*6 steps, about 6 minutes.*

1. **Take a whole thing in one key.** When what you want lines up with a word, a line, a paragraph, a sentence or a block, there is a key for it and you do not have to know where it starts.
   - Keys: Ctrl+Shift+H
   - You should hear: "Selected paragraph", and how many words that was.

2. **Grow and shrink.** From whatever you have, step outwards a level at a time -- word, line, sentence, paragraph, block, everything -- and back in again. Each step says the scope it took.
   - Keys: Ctrl+Shift+X
   - You should hear: The new scope, and its word count.

3. **Mark a spot and walk to the end of it.** For anything that does not line up with a structure. Drop a marker, then move however you like -- arrows, Find, Go To Line, a bookmark -- and take everything between. No modifier held the whole way.
   - Keys: F8
   - You should hear: The line and column where the marker went down.

4. **Finish it, and hear how far it reached.** The span is worked out now, from the marker and where you actually are. That is why you can use Find in between: its own selection does not get in the way.
   - Keys: Shift+F8
   - You should hear: How many words, and the lines it ran between.
   - Worth knowing: That line range is the only selection that carries one, because it is the only one whose reach you cannot work out from its name.

5. **Or hold the Shift down without holding it.** Extend Selection Mode is the third answer: turn it on and every arrow extends instead of moving, with no modifier and no "selected" from your screen reader on every press.
   - Keys: Alt+Shift+F9
   - You should hear: "Extend selection mode on", and where it started.

6. **Check what you have before you replace it.** There is no glance that confirms a selection is the one you meant, and the next character you type replaces it. Say Selection reads it back; long ones are summarised rather than read in full.
   - Keys: Ctrl+Shift+Y
   - You should hear: The selection, or a summary of it with its size.

Put back the one you just lost with Reselect. It remembers every way of selecting, not only the marker.

Next: Finding your way back.

### Finding your way back

Bookmarks, marks and the Back key -- three things that sound alike and answer different questions.

*4 steps, about 5 minutes.*

1. **Keep a place you mean to come back to.** Nine numbered bookmarks, per file, and they are still there tomorrow. A bookmark survives editing: it remembers the words around it, so inserting three paragraphs above one does not move it off its line.
   - Keys: Ctrl+Shift+1
   - You should hear: The bookmark's number, and the line it went on.

2. **Drop a pin you will forget.** A mark is different: it is where you were standing before you went to look something up. No number, no label, no list. Pop Mark uses it up getting back.
   - Keys: Ctrl+Shift+M
   - You should hear: The line, and how many marks you now have.

3. **Go and look something up, then come back.** Move a long way off -- Ctrl+End will do -- and pop the mark.
   - Keys: Ctrl+M
   - You should hear: The line you came back to, and how many marks are left.

4. **Undo the jump.** Back is the undo for navigation. Every jump in QuillLite goes through it -- bookmarks, marks, headings, Go To, search results -- so there is no jump it cannot take you back from.
   - Keys: Alt+Left
   - You should hear: Where you were before the jump.
   - Worth knowing: Without this, every jump is one-way: you followed a heading and have no way back to the paragraph you were writing except a line number nobody told you.

Next: Skimming something long.

### Skimming something long

What a sighted reader gets from scrolling and glancing, and the three ways to get it without one.

*5 steps, about 5 minutes.*

1. **Ask for the shape.** The headings list is every heading in the document, in order, each reading its level and its text. Enter goes there.
   - Keys: Ctrl+Alt+L
   - You should hear: Each heading, with its level.

2. **Walk it instead.** Next and Previous Heading move by structure rather than by line, and each arrival says the level and the text.
   - Keys: Ctrl+Alt+H
   - You should hear: "Heading 2", and the heading's words.

3. **Skim by section.** Walking sections says the heading, whether it is folded, and **how many lines are under it**. That last part is the glance: it is how you find out a section is enormous without reading any of it.
   - Keys: Ctrl+Alt+Shift+Down
   - You should hear: The heading, its state, and its size in lines.

4. **Mark one as dealt with.** Folding a section is a note to yourself. Nothing is hidden from the cursor and Find still finds things inside it -- you simply hear that it is folded when you pass by.
   - Keys: Ctrl+Shift+F9
   - You should hear: How many lines went with it.

5. **Rearrange it, if the shape is wrong.** The Heading Organizer is every heading as one list. Tab demotes, Shift+Tab promotes, and Move Up and Move Down take the heading and everything under it.
   - Keys: Alt+Shift+O
   - You should hear: Each heading as you arrow, with a preview of its section.
   - Worth knowing: Nothing changes until Apply, and one Ctrl+Z puts it all back.

### Spelling, without a red squiggle

How QuillLite tells you a word is wrong without interrupting the sentence you are writing, and the one key that fixes it.

*4 steps, about 5 minutes.*

1. **Type something wrong, and keep going.** A moment after you finish the word, the status bar says it may be misspelled. It is not spoken over your typing, because a spell checker that interrupts the sentence you are writing is one people switch off.
   - You should hear: Nothing, unless you asked for a sound or a sentence in Preferences.

2. **Fix the word you are standing in.** The Applications key is your squiggle. Press it with the cursor in the word, and **the first Down arrow lands on a suggestion**. Enter replaces it; the cursor does not move and no dialog opens.
   - Keys: Applications, Shift+F10
   - You should hear: The suggestions, in order, as you arrow.
   - Worth knowing: Everything else about the word -- ignore, teach, next, previous -- is one row below the suggestions, in the same place every time.

3. **Teach it a word.** Your own dictionary keeps it for good. The document's own keeps it beside the file, so anybody who opens that file gets it too -- which is the right home for a product name and the wrong one for your surname.
   - You should hear: Which of the two it was added to, by name.

4. **Check the whole thing.** F7 walks the document one word at a time. It starts where your cursor is and offers to carry on from the beginning when it reaches the end.
   - Keys: F7
   - You should hear: Each word, its suggestions, and a summary of what changed at the end.

Spelling stays quiet in source and configuration files whatever the settings say -- every identifier in one would be a false alarm.
