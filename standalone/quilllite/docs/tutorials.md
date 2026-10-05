# QUILL Lite Tutorials

Welcome. There are 10 short lessons here, about 48 minutes in all, and you can take them in any order. Each one is a few small steps, and each step tells you what to press and what you should hear.

This page is the lessons written out, so you can read them anywhere. If you would rather be walked through, open **Help > Tutorials... (Ctrl+Alt+F1)** in QUILL Lite. It does a step for you when you ask, and moves on by itself once it hears you have done one.

The keys here are the ones QUILL Lite comes with. If you have changed a key, the lessons inside the app use your key; this page cannot know about the change.

## Contents

- **Your first documents**: Start here. Open a file and save it back unchanged, find out where the facts about it live and what kind of document you are in, and move between the documents you have open.
  - Open a file, and give it back unchanged (5 minutes)
  - Four kinds of document, and how to say which (4 minutes)
  - Your documents are numbered (3 minutes)
  - What to press when you are lost (3 minutes)
- **Working in a document**: Once you are comfortable: select more than a few words, find your way back to where you were, skim something long, fix spelling without a red squiggle, ask a question about the document in front of you, and write by talking.
  - Selecting more than a few words (6 minutes)
  - Finding your way back (5 minutes)
  - Skimming something long (5 minutes)
  - Spelling, without a red squiggle (5 minutes)
  - Asking a question about a document (6 minutes)
  - Write by talking (6 minutes)

## Your first documents

Start here. Open a file and save it back unchanged, find out where the facts about it live and what kind of document you are in, and move between the documents you have open.

### Open a file, and give it back unchanged

Start here. You open a file you already have, hear the three things QUILL Lite remembers about it, and save it back exactly as it was.

*5 steps, about 5 minutes.*

1. **Open something you already have.** Pick any text file you already have. An older one is a good test. QUILL Lite opens plain text, Markdown, HTML and rich text, so whatever you choose will be fine.
   - Keys: Ctrl+O
   - You should hear: The file's name, and the first line of it.

2. **Look at what it remembered.** Now go to the status bar. It is a row of cells, and you move along it with the arrow keys. Listen for three of them: Encoding is how the letters are stored, Line Endings is how each line finishes, and Format is the kind of document. QUILL Lite keeps all three just as it found them.
   - Keys: F6
   - You should hear: Each cell's name and its value as you arrow along.
   - Worth knowing: Press Escape to go back to your document. Looking around is safe: nothing changes unless you press Enter on a cell and answer the question it asks.

3. **Save it without changing anything.** Save the file straight back without typing anything. If you like, compare it with a copy of the original afterwards. You will find they are the same, byte for byte.
   - Keys: Ctrl+S
   - You should hear: "Saved" and the file's name.

4. **Find it again later.** QUILL Lite remembers what you open. Open the Recent Documents window and your file is at the top of the list. Next time, press Enter on it instead of hunting for it with Open. Alt Shift 1 reopens the newest one without opening the window at all.
   - Keys: Alt+Shift+0
   - You should hear: The Recent Documents window, on your file's name and its folder.
   - Worth knowing: Press Escape to close the window. Pin, in the same window, keeps a file you use often at the top for good.

5. **Type a character the file cannot hold.** This one is optional. If your file uses an older encoding, type an em dash or an emoji and save again. QUILL Lite stops and asks you first: save as UTF-8 and keep the character, save as it was and lose it, or cancel. You decide.
   - You should hear: A question counting the characters, naming the encoding, and offering Yes, No and Cancel.
   - Worth knowing: Not sure which encoding your file uses? The Encoding cell in the status bar tells you.

That is the heart of QUILL Lite. Your file comes back the way you left it, and everything else is built on top of that.

Next: Four kinds of document, and how to say which.

### Four kinds of document, and how to say which

Plain text, Markdown, HTML and rich text: what each one means for you, and the one key that moves between them.

*4 steps, about 4 minutes.*

1. **Find out what you are in.** Go to the status bar and arrow to the Format cell. It tells you which kind of document this is. QUILL Lite guesses from the file's name, and you can always change its mind.
   - Keys: F6
   - You should hear: The Format cell, reading "Markdown", "HTML", "Plain text" or "Rich text".

2. **Ring through the four.** One key steps through all four kinds, and each one says its name as you land on it. Keep pressing until you hear the one you want. Moving between plain text, Markdown and HTML does not touch your words. It only changes what the formatting keys type from now on.
   - Keys: Alt+Shift+F
   - You should hear: Each kind naming itself as you land on it.

3. **Go into rich text, and come back.** Rich text is the one stop that really converts. Going in turns Markdown into real bold, headings and lists. Coming back out turns them into Markdown again, and QUILL Lite asks you first, naming anything it cannot carry across.
   - You should hear: A question before it converts, then "Rich text mode" or "Plain text mode".
   - Worth knowing: Your file keeps its name. A rich document cannot be saved over a .txt file, so the next Ctrl+S offers you the right ending already filled in.

4. **Say otherwise, for this window only.** Sometimes you want to write HTML in a scratch .txt file, and that is fine. Document Language lets you pick the kind yourself, and tells you what each choice will do before you choose. Your choice lasts as long as this window is open.
   - Keys: Ctrl+Alt+F6
   - You should hear: Each option described, and the one the file name would have chosen marked.

Now you know what kind of document you are in, and how to change it when QUILL Lite guessed wrong.

Next: Your documents are numbered.

### Your documents are numbered

Instead of tabs, every open document gets a number. Here are the ways to get to the one you want.

*3 steps, about 3 minutes.*

1. **Open a second file.** It opens inside the same window, as document 2. A number is easy to remember and easy to say: "document 3" is much clearer than "the other Untitled".
   - Keys: Ctrl+O
   - You should hear: The new document's number and name, in its title.

2. **Walk between them.** Ctrl+Tab is what most people press, and Ctrl+F6 is the key Windows uses for this. Both work. The Window menu lists them too.
   - Keys: Ctrl+Tab
   - You should hear: The document you arrive at, announcing its number and name.

3. **Go straight to one.** Hold Alt and press a document's number to go straight to it. Once you have more than two open, this is the quickest way around, and it is why they have numbers.
   - Keys: Alt+1, Alt+2, Alt+3
   - You should hear: The document you asked for.
   - Worth knowing: Your documents all live inside one QUILL Lite window, so they do not appear in Alt+Tab. Use the keys in this lesson to move between them instead.

Open as many as you like. Each one has a number, and Alt with that number takes you straight there.

### What to press when you are lost

Three keys that tell you where you are, what something does, and what QUILL Lite can do.

*3 steps, about 3 minutes.*

1. **Ask what you are standing on.** F1 works everywhere: in your document, on a button, in any window. It tells you what the window is for, and then what the thing you are on does.
   - Keys: F1
   - You should hear: The window's purpose, then the control's.

2. **Ask what the facts are.** The status bar holds everything QUILL Lite knows about your document, plus the last thing it said. Missed a message? It is waiting in the last cell, Status Message. Press End to jump there.
   - Keys: F6
   - You should hear: "Status bar" and the cell you land on, then each fact as you arrow.

3. **Ask what exists.** The Keyboard Shortcuts window lists every key QUILL Lite has. It shows your keys, including any you have changed, and you can type part of a name to find one.
   - Keys: Ctrl+F1
   - You should hear: A searchable list of every command and its key.

Whenever you are unsure, one of these three keys will explain where you are.

## Working in a document

Once you are comfortable: select more than a few words, find your way back to where you were, skim something long, fix spelling without a red squiggle, ask a question about the document in front of you, and write by talking.

### Selecting more than a few words

Three different ways to select a stretch of text without seeing it, and when each one is the easiest.

*6 steps, about 6 minutes.*

1. **Take a whole thing in one key.** If what you want is a whole word, line, sentence, paragraph or block, there is a key for it. You do not need to find where it starts. Try it now on the paragraph you are in.
   - Keys: Ctrl+Shift+H
   - You should hear: "Selected paragraph", and how many words that was.

2. **Grow and shrink.** Starting from whatever you have, you can grow the selection one step at a time: word, line, sentence, paragraph, block, then everything. You can shrink it back the same way. Each step tells you what it took.
   - Keys: Ctrl+Shift+X
   - You should hear: The new scope, and its word count.

3. **Mark a spot and walk to the end of it.** For anything that is not a neat word, line or paragraph. Drop a marker where the selection should start. Then move any way you like, with the arrows, Find, Go To Line or a bookmark. You do not have to hold any key down while you go.
   - Keys: F8
   - You should hear: The line and column where the marker went down.

4. **Finish it, and hear how far it reached.** When you reach the end, finish the selection. Everything between the marker and where you are now is selected. You can even use Find on the way, and it will not spoil it.
   - Keys: Shift+F8
   - You should hear: How many words, and the lines it ran between.
   - Worth knowing: Hearing the line numbers is a quick way to check you caught the stretch you meant.

5. **Or hold the Shift down without holding it.** Here is a third way. Turn on Extend Selection Mode, and every arrow key selects as it moves, just as if you were holding Shift. Your screen reader does not say "selected" on every press, either. Turn it off the same way when you are done.
   - Keys: Alt+Shift+F9
   - You should hear: "Extend selection mode on", and where it started.

6. **Check what you have before you replace it.** Before you type over a selection, it is worth checking it is the one you meant, because the next key you type replaces it. Say Selection reads it back to you. A long one is summed up instead of read in full.
   - Keys: Ctrl+Shift+Y
   - You should hear: The selection, or a summary of it with its size.

Lost a selection by accident? Reselect Last Selection puts it back, however you made it.

Next: Finding your way back.

### Finding your way back

Bookmarks, marks and Go Back. They sound alike, but each one helps you in a different moment.

*4 steps, about 5 minutes.*

1. **Keep a place you mean to come back to.** You have nine numbered bookmarks in every file, and they are still there tomorrow. A bookmark stays with its words, so if you add three paragraphs above it, it is still on the right line.
   - Keys: Ctrl+Shift+1
   - You should hear: The bookmark's number, and the line it went on.

2. **Drop a pin you will forget.** A mark is quicker and lighter. It just remembers where you were before you went to look something up. There is no number and no list. Pop Mark takes you back and then forgets it.
   - Keys: Ctrl+Shift+M
   - You should hear: The line, and how many marks you now have.

3. **Go and look something up, then come back.** Move a long way off. Ctrl+End, the end of the document, will do. Now pop the mark, and you are back where you were.
   - Keys: Ctrl+M
   - You should hear: The line you came back to, and how many marks are left.

4. **Undo the jump.** Go Back works like the Back button in a web browser. Every jump in QUILL Lite can be undone with it: bookmarks, marks, headings, Go To and search results. So you can always get back to where you were.
   - Keys: Alt+Left
   - You should hear: Where you were before the jump.
   - Worth knowing: This is handy after following a heading. One key brings you back to the paragraph you were writing.

Bookmarks are for places you will come back to tomorrow. A mark is for right now. Go Back is for any jump you did not mean.

Next: Skimming something long.

### Skimming something long

Get a feel for a long document the way a sighted reader does by scrolling, using its headings instead.

*5 steps, about 5 minutes.*

1. **Ask for the shape.** The headings list shows every heading in the document, in order. Each one tells you its level and its words. Press Enter on one to go there.
   - Keys: Ctrl+Alt+L
   - You should hear: Each heading, with its level.

2. **Walk it instead.** Next Heading and Previous Heading move from heading to heading instead of line by line. Each time you arrive, you hear the level and the words.
   - Keys: Ctrl+Alt+H
   - You should hear: "Heading 2", and the heading's words.

3. **Skim by section.** Moving by section tells you the heading, whether it is folded, and **how many lines are under it**. That last part is your glance. It tells you a section is huge without reading any of it.
   - Keys: Ctrl+Alt+Shift+Down
   - You should hear: The heading, its state, and its size in lines.

4. **Mark one as dealt with.** Folding a section is a note to yourself that you are done with it. Nothing is hidden: your cursor still goes in and Find still finds things there. You just hear that it is folded as you pass.
   - Keys: Ctrl+Shift+F9
   - You should hear: How many lines went with it.

5. **Rearrange it, if the shape is wrong.** The Heading Organizer shows every heading as one list. Tab makes a heading one level lower, Shift+Tab one level higher, and Move Up and Move Down carry the heading along with everything under it.
   - Keys: Alt+Shift+O
   - You should hear: Each heading as you arrow, with a preview of its section.
   - Worth knowing: Nothing changes until you press Apply, and one Ctrl+Z puts it all back.

With headings, a long document becomes something you can move around in quickly, a section at a time.

### Spelling, without a red squiggle

How QUILL Lite lets you know a word looks wrong without breaking into your sentence, and the one key that fixes it.

*4 steps, about 5 minutes.*

1. **Type something wrong, and keep going.** Type a word wrong on purpose and carry on. A moment after you finish the word, the status bar notes that it may be misspelled. Nothing is spoken over your typing, so you can finish your thought first.
   - You should hear: Nothing, unless you asked for a sound or a sentence in Preferences.

2. **Fix the word you are standing in.** The Applications key is your red squiggle. Put the cursor in the word and press it. **The first Down arrow lands on a suggestion**. Press Enter to use it. Your cursor stays put and no dialog opens.
   - Keys: Applications, Shift+F10
   - You should hear: The suggestions, in order, as you arrow.
   - Worth knowing: Everything else you can do with the word, like ignore it, add it, or go to the next or previous one, is in the same menu just below the suggestions.

3. **Teach it a word.** You can add a word to your own dictionary, and it is known for good. Or add it to the document's dictionary, which travels with that file, so anyone who opens it gets the word too. That suits a product name better than your surname.
   - You should hear: Which of the two it was added to, by name.

4. **Check the whole thing.** F7 goes through the document one word at a time. It starts where your cursor is, and when it reaches the end it offers to carry on from the beginning.
   - Keys: F7
   - You should hear: Each word, its suggestions, and a summary of what changed at the end.

One more thing: spelling stays quiet in program code and settings files, whatever your settings say, so you are not told about every made-up name in them.

### Asking a question about a document

AI help is the one feature that sends anything off your computer. Here is how to turn it on, what is sent when you use it, and what it will not do.

*5 steps, about 6 minutes.*

1. **Turn it on, and agree to it separately.** AI help stays off until two things are true: the feature is switched on, and you have said yes to the privacy agreement. These are two separate steps, so nothing is ever sent just because a profile, a settings file or someone else switched the feature on. Only your own yes counts.
   - Keys: Ctrl+Alt+Shift+K
   - You should hear: The agreement, read out in full before you are asked.
   - Worth knowing: You can reach the agreement three ways: this command, a check box in Preferences, or switching AI help on in Customize Features. You can always open it to read it, whether or not you have agreed.

2. **Connect this computer, once.** There is no account, no password and no email address. You are given an eight-character code. Open the web page on anything with a browser, this computer or your phone, and type the code in. Asking for the code is the first moment anything is sent.
   - Keys: Ctrl+Alt+Shift+F10
   - You should hear: The code, character by character, and the window confirming in place rather than opening another one.
   - Worth knowing: Each computer connects on its own. Signing one out leaves the others connected.

3. **Ask about what is in front of you.** Type a question about the open document, like 'what does this say about the deadline'. The answer comes back along with the part of the document it came from, so you can go and read that part yourself.
   - Keys: Ctrl+Alt+Z
   - You should hear: The passages it chose, before anything is sent, and then the answer.
   - Worth knowing: Long documents are fine. It does not send the whole file. It picks the three passages most likely to answer you and sends only those.

4. **Or hand it a job.** The AI pad has five rows. Four of them work on what you have selected, or on the paragraph or section you pick with Send this much: summarize it, rewrite it clearer and shorter, proofread it, or explain a tricky passage. The fifth is the question you just asked. Nothing changes in your document by itself. The answer comes with Replace My Selection, Insert Below and Copy underneath, and you choose.
   - Keys: Ctrl+Alt+G
   - You should hear: What is about to be sent, before it goes.

5. **Know what you have left.** The service is free, so it has limits. One question can carry about two thousand two hundred and fifty words of your document, and you get a hundred requests a month. If what you asked about is too big, you are told in plain words before anything is sent, so you can select less and try again.
   - Keys: Ctrl+Alt+Shift+F9
   - You should hear: What you have used and what is left.
   - Worth knowing: The limits can change from time to time. Usage always shows the numbers that apply to you right now.

What is kept is how many requests you made and how big they were. What you wrote, and what came back, is not kept.

### Write by talking

Dictate a few sentences into a document, take one back, hold the key to talk, and find the settings. Everything stays on your computer.

*6 steps, about 6 minutes.*

1. **Start dictation.** Put the cursor where the words should go, and turn dictation on. The first time, it takes a second or two to get ready.
   - Keys: Ctrl+F11
   - You should hear: Two rising tones, and "Dictation on".

2. **Say a sentence, and pause.** Talk the way you would to a friend, then stop for a moment. You do not need to say the punctuation: full stops, commas and capitals are put in for you.
   - You should hear: A soft tone, then the words that were written, read back.

3. **Take a phrase back.** Say scratch that, on its own, after a pause. Only the last phrase you said goes; anything you typed is left alone.
   - You should hear: "Scratched:" and the words that went.

4. **Turn it off, then hold the key and talk.** Press the dictation key once to turn it off. Now hold the same key down, say a sentence, and let go. Dictation writes your last phrase and turns itself off. A quick press still turns it on and leaves it on.
   - Keys: Ctrl+F11
   - You should hear: "Dictation on" while you hold, then "Dictation off" after your words.

5. **See the phrases you said.** Recent Phrases lists what you dictated this session, newest first. Enter writes one at the cursor again, which rescues a scratch that that went one too far.
   - Keys: Shift+F11
   - You should hear: Recent Phrases, on the newest phrase.

6. **Find the settings.** Dictation Settings has the speech engine, the microphone and what you hear after each phrase. More Dictation Settings, inside it, has holding the key, the words heard while you speak, and talking to the AI.
   - Keys: Alt+Shift+F6
   - You should hear: Dictation Settings, on Speech engine.
   - Worth knowing: Nothing you say leaves the computer unless you choose OpenAI as the speech engine with your own key, and agree to it.

You can now write by talking, take back a phrase, and hold the key to talk. Say what can I say while dictating to hear everything it understands; the user guide's dictation chapter has the rest.
