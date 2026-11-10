# What you can say in each app

This page is made from the command catalogue, the one list every QUILL family app reads to understand what you type or say to it. Do not edit it by hand; run `python -m quill.tools.build_command_catalogue_reference --write`.

Each command has a name, its key when it has one, what it does, and some of the ways you might ask for it. The Command Palette (Ctrl+Shift+P) finds a command by these words as well as by its name. Commands that change or lose something ask first.

## QUILL

53 commands can be asked for in a sentence here.

### QUILL: Edit

- **Find (Ctrl+F).** Find words in the document.
  Say: "find a word"; "search the document"; "look for something".
- **Find Next (F3).** Find the next match of what you last searched for.
  Say: "find the next one"; "next match please"; "search again".
- **Redo (Ctrl+Y).** Put back the change you just undid.
  Say: "redo that change"; "put the change back"; "redo what I undid".
- **Say Selection (Ctrl+Shift+Y).** Read out what is selected.
  Say: "what have I selected"; "read me the selected text"; "say the selection".
- **Select All.** Select the whole document.
  Say: "select the whole document"; "select everything"; "highlight all the text".
- **Undo (Ctrl+Z).** Take back the last change.
  Say: "undo the last change"; "oops take that back"; "revert my last edit".

### QUILL: File

- **Close Document (Ctrl+W).** Close this document. It asks before it does it.
  Say: "close this document"; "I'm done with this file"; "close it".
- **New Document (Ctrl+N).** Start a new blank document.
  Say: "start a new document"; "give me a blank page"; "new file please".
- **Open (Ctrl+O).** Open a document from a folder.
  Say: "open a document"; "open a file from my folders"; "load a file".
- **Print (Ctrl+P).** Print this document.
  Say: "print this"; "print the document"; "send it to the printer".
- **Recent Documents (Alt+Shift+0).** Open a document you had open recently.
  Say: "open my last document"; "show my recent files"; "what was I working on".
- **Save (Ctrl+S).** Save this document.
  Say: "save this"; "save my document"; "keep my changes".
- **Save All.** Save every open document.
  Say: "save all my documents"; "save every file"; "save everything that is open".
- **Save As (Ctrl+Shift+S).** Save a copy of this document under a new name or in another place.
  Say: "save this under a new name"; "save a copy"; "save it somewhere else".

### QUILL: Format

- **Bigger Text (Ctrl+Shift+.).** Make the selected text's font bigger in the document itself.
  Say: "make the text bigger"; "bigger font"; "increase the font size".
- **Bold (Ctrl+B).** Make the selected text bold (rich documents only).
  Say: "make this bold"; "bold the selection"; "put it in bold".
- **Bulleted List.** Start a bulleted list.
  Say: "start a bulleted list"; "make a list with bullets"; "add bullet points".
- **Italic (Ctrl+I).** Make the selected text italic (rich documents only).
  Say: "make this italic"; "put it in italics"; "italicise the selection".
- **Lower Case (Ctrl+Shift+K).** Change the selection to small letters.
  Say: "make this lower case"; "no capitals in this bit"; "change it to small letters".
- **Numbered List.** Start a numbered list.
  Say: "start a numbered list"; "make a list with numbers"; "number these lines".
- **Sentence Case (Ctrl+Alt+Shift+U).** Capitalise only the first word of each sentence.
  Say: "make this sentence case"; "fix the capitals like a sentence"; "sentence case please".
- **Smaller Text (Ctrl+Shift+,).** Make the selected text's font smaller in the document itself.
  Say: "make the text smaller"; "smaller font"; "decrease the font size".
- **Title Case (Ctrl+Shift+T).** Capitalise each main word of the selection.
  Say: "make this title case"; "capitalise each word"; "turn it into a title".
- **Upper Case (Ctrl+Shift+U).** Change the selection to capital letters.
  Say: "make this all capitals"; "change it to upper case"; "shout this part".

### QUILL: Help

- **Command Palette (Ctrl+Shift+P).** Show every command, to search them.
  Say: "show me every command"; "open the command palette"; "list all the commands".
- **What Can I Say Here (Ctrl+Alt+Shift+F1).** List what you can say or do in this window.
  Say: "what can I do in this window"; "list what I can say here"; "what are my options".

### QUILL: Navigate

- **Clear Bookmarks (Ctrl+Alt+B).** Remove every bookmark in this document. It asks before it does it.
  Say: "clear all my bookmarks"; "remove every bookmark"; "get rid of the bookmarks".
- **Go to Anything (Ctrl+Alt+Shift+A).** Move to a heading, bookmark or line by name.
  Say: "go to anything"; "jump to a heading by name"; "take me somewhere".
- **Go to Line (Ctrl+G).** Move to a line by its number.
  Say: "go to line 120"; "jump to line 5"; "take me to line 40".
- **Headings List (Ctrl+Shift+O).** Show the headings, to move to one.
  Say: "show me the headings"; "list the headings"; "open the outline".
- **Next Bookmark (F2).** Move to the next bookmark.
  Say: "go to the next bookmark"; "jump to my next bookmark"; "next bookmark please".
- **Next Heading (Ctrl+Alt+H).** Move to the next heading.
  Say: "go to the next heading"; "jump to the next section"; "next heading please".
- **Parameter Hints.** Say which argument of the call at the cursor you are on, and its signature.
  Say: "which parameter am I on"; "what arguments does this take"; "say the signature".
- **Previous Heading (Ctrl+Alt+Shift+H).** Move to the previous heading.
  Say: "go back a heading"; "jump to the previous section"; "previous heading please".
- **Say Time and Date (Alt+Shift+Space).** Say the time and the date.
  Say: "what time is it"; "what is today's date"; "tell me the time".
- **Set Bookmark (Ctrl+Shift+B).** Bookmark this spot.
  Say: "bookmark this spot"; "put a bookmark here"; "remember this place".
- **Where Am I (Ctrl+Shift+Grave, Q).** Say where you are and the state of the document.
  Say: "where am I"; "what is the state of this document"; "tell me where I am".

### QUILL: Tools

- **Next Misspelling (Ctrl+F7).** Move to the next misspelled word.
  Say: "go to the next spelling mistake"; "find the next typo"; "next misspelled word".
- **Open WordPress Workbench (Ctrl+Alt+Shift+Grave, H).** Open the window for your WordPress sites.
  Say: "open the wordpress workbench"; "show me my wordpress sites"; "what needs me on my sites".
- **Read Aloud (Ctrl+Shift+Grave, R).** Read the document aloud, or pause reading.
  Say: "read this to me"; "read the document out loud"; "pause the reading".
- **Sounds On or Off (Alt+Shift+M).** Turn QUILL's sounds on or off.
  Say: "turn the sounds off"; "stop the beeps"; "sounds back on".
- **Spelling (F7).** Check the spelling of the document.
  Say: "check my spelling"; "run the spell checker"; "are there any spelling mistakes".
- **Stop Reading Aloud (Ctrl+Shift+Grave, Shift+R).** Stop reading the document aloud.
  Say: "stop reading to me"; "stop reading aloud"; "that is enough reading".
- **Word Count (Ctrl+Shift+G).** Say how many words the document has.
  Say: "how many words is this"; "how long is this document"; "count the words".
- **Word Summary (Ctrl+Alt+Shift+[).** The full statistics: words, sentences, paragraphs and more.
  Say: "give me the word summary"; "how many sentences are there"; "document statistics".

### QUILL: View

- **Check Spelling As I Type (Ctrl+Alt+F7).** Check spelling while you type, or stop.
  Say: "check my spelling as I type"; "stop checking spelling while I type"; "live spelling on".
- **Meeting Mode (Ctrl+Shift+Grave, Shift+M).** Stay quiet while you are in a meeting.
  Say: "I'm in a meeting"; "turn meeting mode on"; "meeting mode off".
- **Normal Zoom (Ctrl+0).** Show the text at its normal size on screen.
  Say: "reset the zoom"; "back to normal size"; "normal zoom please".
- **Quiet Mode (Ctrl+Shift+Grave, Shift+Q).** Make QUILL say less as you work, or talk as usual again.
  Say: "talk less"; "be less chatty"; "turn quiet mode on".
- **Say Headings As I Move (Ctrl+Alt+F3).** Say each heading you move onto, or stop.
  Say: "tell me the headings as I move"; "stop announcing headings"; "announce headings".
- **Word Wrap (Alt+Z).** Wrap long lines to the window, or stop wrapping.
  Say: "turn word wrap on"; "stop wrapping lines"; "wrap the long lines".
- **Zoom In (Ctrl+=).** Magnify the view on screen, without changing the document.
  Say: "zoom in"; "make it larger on screen"; "magnify the text".
- **Zoom Out (Ctrl+-).** Make the view on screen smaller, without changing the document.
  Say: "zoom out"; "make it smaller on screen"; "less magnified".

### QUILL: only from its menu or key

These are never done from a sentence, because they send, delete, sign in, change settings or leave the app. Each is still on its menu and its key.

- Check for Updates: Help, Check for Updates.
- Compare Braille Surfaces: Help, Troubleshooting.
- Copy a Diagnostic Summary: Help, Troubleshooting.
- Copy to the Next Tray Slot: Edit, Copy Tray.
- Dark Mode: View, Dark Mode.
- Exit: File, Exit.
- Language Servers: Navigate, Code, Language Servers.
- Open a Web Address: File, Open a Web Address.
- Preferences Hub: Tools, Preferences Hub.
- Replace All: Edit, Replace.
- Report the Editor Surface: Help, Troubleshooting.
- Restore a Backup: File, Restore a Backup.
- Save to GitHub: the GitHub menu.
- Save to Remote: File, Save to Remote.
- Say or Type a Command: F11.
- Send to Tray: View, Send to Tray.
- Settings: Tools, Settings.
- Speech and Braille Self-Test: Help, Troubleshooting.
- Where Am I, in Detail: Navigate, Where Am I.

## QUILL Lite

44 commands can be asked for in a sentence here.

### QUILL Lite: Edit

- **Find (Ctrl+F).** Find words in the document.
  Say: "find a word"; "search the document"; "look for something".
- **Find Next (F3).** Find the next match of what you last searched for.
  Say: "find the next one"; "next match please"; "search again".
- **Redo (Ctrl+Y).** Put back the change you just undid.
  Say: "redo that change"; "put the change back"; "redo what I undid".
- **Say Selection (Ctrl+Shift+Y).** Read out what is selected.
  Say: "what have I selected"; "read me the selected text"; "say the selection".
- **Undo (Ctrl+Z).** Take back the last change.
  Say: "undo the last change"; "oops take that back"; "revert my last edit".

### QUILL Lite: File

- **Close Document (Ctrl+W).** Close this document. It asks before it does it.
  Say: "close this document"; "I'm done with this file"; "close it".
- **New Document (Ctrl+N).** Start a new blank document.
  Say: "start a new document"; "give me a blank page"; "new file please".
- **Open (Ctrl+O).** Open a document from a folder.
  Say: "open a document"; "open a file from my folders"; "load a file".
- **Print (Ctrl+P).** Print this document.
  Say: "print this"; "print the document"; "send it to the printer".
- **Recent Documents (Alt+Shift+0).** Open a document you had open recently.
  Say: "open my last document"; "show my recent files"; "what was I working on".
- **Save (Ctrl+S).** Save this document.
  Say: "save this"; "save my document"; "keep my changes".
- **Save As (Ctrl+Shift+S).** Save a copy of this document under a new name or in another place.
  Say: "save this under a new name"; "save a copy"; "save it somewhere else".

### QUILL Lite: Format

- **Bigger Text (Ctrl+Shift+.).** Make the selected text's font bigger in the document itself.
  Say: "make the text bigger"; "bigger font"; "increase the font size".
- **Bold (Ctrl+B).** Make the selected text bold (rich documents only).
  Say: "make this bold"; "bold the selection"; "put it in bold".
- **Italic (Ctrl+I).** Make the selected text italic (rich documents only).
  Say: "make this italic"; "put it in italics"; "italicise the selection".
- **Lower Case (Ctrl+Shift+K).** Change the selection to small letters.
  Say: "make this lower case"; "no capitals in this bit"; "change it to small letters".
- **Sentence Case (Ctrl+Alt+Shift+U).** Capitalise only the first word of each sentence.
  Say: "make this sentence case"; "fix the capitals like a sentence"; "sentence case please".
- **Smaller Text (Ctrl+Shift+,).** Make the selected text's font smaller in the document itself.
  Say: "make the text smaller"; "smaller font"; "decrease the font size".
- **Title Case (Ctrl+Shift+T).** Capitalise each main word of the selection.
  Say: "make this title case"; "capitalise each word"; "turn it into a title".
- **Upper Case (Ctrl+Shift+U).** Change the selection to capital letters.
  Say: "make this all capitals"; "change it to upper case"; "shout this part".

### QUILL Lite: Help

- **Command Palette (Ctrl+Shift+P).** Show every command, to search them.
  Say: "show me every command"; "open the command palette"; "list all the commands".
- **What Can I Say Here (Ctrl+Alt+Shift+F1).** List what you can say or do in this window.
  Say: "what can I do in this window"; "list what I can say here"; "what are my options".

### QUILL Lite: Navigate

- **Clear Bookmarks (Ctrl+Alt+B).** Remove every bookmark in this document. It asks before it does it.
  Say: "clear all my bookmarks"; "remove every bookmark"; "get rid of the bookmarks".
- **Go to Anything (Ctrl+Alt+Shift+A).** Move to a heading, bookmark or line by name.
  Say: "go to anything"; "jump to a heading by name"; "take me somewhere".
- **Go to Line (Ctrl+G).** Move to a line by its number.
  Say: "go to line 120"; "jump to line 5"; "take me to line 40".
- **Headings List (Ctrl+Alt+L).** Show the headings, to move to one.
  Say: "show me the headings"; "list the headings"; "open the outline".
- **Next Bookmark (F2).** Move to the next bookmark.
  Say: "go to the next bookmark"; "jump to my next bookmark"; "next bookmark please".
- **Next Heading (Ctrl+Alt+H).** Move to the next heading.
  Say: "go to the next heading"; "jump to the next section"; "next heading please".
- **Parameter Hints.** Say which argument of the call at the cursor you are on, and its signature.
  Say: "which parameter am I on"; "what arguments does this take"; "say the signature".
- **Previous Heading (Ctrl+Alt+Shift+H).** Move to the previous heading.
  Say: "go back a heading"; "jump to the previous section"; "previous heading please".
- **Say Time and Date (Alt+Shift+Space).** Say the time and the date.
  Say: "what time is it"; "what is today's date"; "tell me the time".
- **Set Bookmark (Ctrl+Shift+B).** Bookmark this spot.
  Say: "bookmark this spot"; "put a bookmark here"; "remember this place".

### QUILL Lite: Tools

- **Next Misspelling (Ctrl+F7).** Move to the next misspelled word.
  Say: "go to the next spelling mistake"; "find the next typo"; "next misspelled word".
- **Open WordPress Workbench (Ctrl+Alt+Shift+Grave, H).** Open the window for your WordPress sites.
  Say: "open the wordpress workbench"; "show me my wordpress sites"; "what needs me on my sites".
- **Sounds On or Off (Alt+Shift+M).** Turn QUILL's sounds on or off.
  Say: "turn the sounds off"; "stop the beeps"; "sounds back on".
- **Spelling (F7).** Check the spelling of the document.
  Say: "check my spelling"; "run the spell checker"; "are there any spelling mistakes".
- **Word Count (Ctrl+Shift+G).** Say how many words the document has.
  Say: "how many words is this"; "how long is this document"; "count the words".
- **Word Summary (Ctrl+Alt+Shift+[).** The full statistics: words, sentences, paragraphs and more.
  Say: "give me the word summary"; "how many sentences are there"; "document statistics".

### QUILL Lite: View

- **Check Spelling As I Type (Ctrl+Alt+F7).** Check spelling while you type, or stop.
  Say: "check my spelling as I type"; "stop checking spelling while I type"; "live spelling on".
- **Normal Zoom (Ctrl+0).** Show the text at its normal size on screen.
  Say: "reset the zoom"; "back to normal size"; "normal zoom please".
- **Say Headings As I Move (Ctrl+Alt+F3).** Say each heading you move onto, or stop.
  Say: "tell me the headings as I move"; "stop announcing headings"; "announce headings".
- **Word Wrap (Alt+Z).** Wrap long lines to the window, or stop wrapping.
  Say: "turn word wrap on"; "stop wrapping lines"; "wrap the long lines".
- **Zoom In (Ctrl+=).** Magnify the view on screen, without changing the document.
  Say: "zoom in"; "make it larger on screen"; "magnify the text".
- **Zoom Out (Ctrl+-).** Make the view on screen smaller, without changing the document.
  Say: "zoom out"; "make it smaller on screen"; "less magnified".

### QUILL Lite: only from its menu or key

These are never done from a sentence, because they send, delete, sign in, change settings or leave the app. Each is still on its menu and its key.

- Check for Updates: Help, Check for Updates.
- Copy to the Next Tray Slot: Edit, Copy Tray.
- Dark Mode: View, Dark Mode.
- Exit: File, Exit.
- Language Servers: Navigate, Code, Language Servers.
- Open a Web Address: File, Open a Web Address.
- Say or Type a Command: F11.
- Settings: Tools, Settings.

## Quill Radio

30 commands can be asked for in a sentence here.

### Quill Radio: Edit

- **Undo (Ctrl+Z).** Undo the last thing you did.
  Say: "undo the last thing"; "put it back how it was"; "take that back".

### Quill Radio: Favourites

- **Favourite This Station (Ctrl+Shift+F).** Save the station on air to your favourites list, or take it off.
  Say: "add this station to my favourites"; "make this a favourite"; "take this off my favourites".
- **Play a Favourite (Alt+Shift+F).** Play one of your favourite stations, by number or by name.
  Say: "play favourite 3"; "play my first favourite"; "put on a favourite station".

### Quill Radio: Playback

- **Fast Forward (Ctrl+Shift+Right).** Go forward in what is playing.
  Say: "skip ahead 30 seconds"; "go forward a bit"; "fast forward".
- **Faster (Ctrl+Shift+Up).** Play faster.
  Say: "play it faster"; "speed it up a bit"; "a lot faster".
- **Jump to Live (Ctrl+Shift+L).** Go back to the live broadcast.
  Say: "go back to live"; "jump to the live broadcast"; "catch up to live".
- **Normal Speed (Ctrl+Shift+0).** Play at normal speed again.
  Say: "back to normal speed"; "reset the speed"; "play at normal speed".
- **Play or Pause (Ctrl+P).** Start the radio, or pause it.
  Say: "play the radio"; "pause it"; "carry on playing".
- **Play the Last Station (Ctrl+L).** Play the station you listened to last.
  Say: "play the last station"; "go back to the station I had on"; "play what I was listening to".
- **Rewind (Ctrl+Shift+Left).** Go back in what is playing.
  Say: "skip back 30 seconds"; "go back a bit"; "rewind".
- **Slower (Ctrl+Shift+Down).** Play slower.
  Say: "play it slower"; "slow it down a bit"; "a lot slower".
- **Stop (Ctrl+.).** Stop the radio.
  Say: "stop the radio"; "turn the radio off"; "stop playing".

### Quill Radio: Recording

- **Record a Station (Ctrl+Alt+R).** Set up a recording of a station you pick from a list. It asks before it does it.
  Say: "record a station"; "record the jazz station"; "set up a recording".
- **Record or Stop Recording (Ctrl+R).** Record what is playing now, or stop recording it. It asks before it does it.
  Say: "record this"; "start recording"; "stop the recording".
- **Recordings (Ctrl+Shift+R).** Show your recordings.
  Say: "show my recordings"; "open the recordings"; "where are my recordings".
- **Stop Every Recording (Ctrl+Alt+X).** Stop every recording that is running. It asks before it does it.
  Say: "stop all the recordings"; "stop every recording"; "end all recordings".

### Quill Radio: Song

- **Identify Song (Ctrl+K).** Find out what song this is.
  Say: "what song is this"; "identify this song"; "who sings this".
- **Lyrics (Ctrl+Alt+B).** Show the words of the song playing.
  Say: "show me the lyrics"; "what are the words to this"; "lyrics please".
- **Say Song Titles (Ctrl+Alt+T).** Say each song's title when it starts, or stop.
  Say: "tell me each song title"; "stop announcing the songs"; "announce titles".
- **Song History (Ctrl+Shift+H).** List the songs that played earlier.
  Say: "what played earlier"; "show the song history"; "what was the last song".
- **What's Playing (Ctrl+T).** Say the song and station playing right now.
  Say: "what's playing"; "what station is this"; "tell me what is on".

### Quill Radio: Stations

- **Browse Stations (Ctrl+B).** Look through the stations to find one.
  Say: "browse the stations"; "find me a station"; "show me the stations".
- **Find Streams on a Website (Ctrl+Alt+S).** Find the radio streams on a web page.
  Say: "find the streams on a website"; "get a station from a web page"; "look for streams on a site".
- **On Now (Ctrl+Alt+H).** Show the programme schedule: the shows on the stations now and later.
  Say: "what's on right now"; "show what is on now"; "what programmes are on".

### Quill Radio: Timers

- **Sleep Timer (Ctrl+Shift+Z).** Stop the radio after a set time, such as in half an hour.
  Say: "sleep in 20 minutes"; "stop playing in an hour"; "set a sleep timer".
- **Wake Timer (Ctrl+Alt+Z).** Start the radio at a time you choose.
  Say: "wake me at 7"; "set a wake timer"; "start the radio in the morning".

### Quill Radio: Volume

- **Mute (Ctrl+M).** Mute the radio, or unmute it.
  Say: "mute the radio"; "unmute it"; "silence it for a moment".
- **Volume Boost (Ctrl+Shift+B).** Make a quiet station louder than full volume allows, or stop boosting.
  Say: "boost this quiet station"; "turn the boost on"; "stop boosting the volume".
- **Volume Down (Ctrl+Down).** Make the radio quieter.
  Say: "turn it down a bit"; "much quieter"; "it's too loud".
- **Volume Up (Ctrl+Up).** Make the radio louder.
  Say: "turn it up a bit"; "much louder"; "I can't hear it".

### Quill Radio: only from its menu or key

These are never done from a sentence, because they send, delete, sign in, change settings or leave the app. Each is still on its menu and its key.

- ChatGPT Account: the AI menu, Accounts and Usage.
- Download Preferences: the Stations menu.
- Export Setup: the File menu.
- Forget Station Volumes: the Volume menu.
- Import Setup: the File menu.
- Say or Type a Command: the Help menu, Alt+F11.
- Suggest a Station: the AI menu.
- Update the Station Catalogue: the Stations menu.
