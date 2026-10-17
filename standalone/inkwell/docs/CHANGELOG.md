# Quill Inkwell changelog

## Unreleased

- **Dictate Anywhere: spell an address with pauses** (2026-10-17). While
  spelling, each phrase now joins the letters you spelled just before it, with
  no space: "start spelling", "juliet oscar", "at sign echo x-ray", "dot
  charlie oscar", "stop spelling" types *jo@ex.co*. Before, every pause typed a
  space into the address. Say "space" for a space. Limit: a whole word such as
  "smith" is not a letter and is left out; spell it.
- **Dictate Anywhere: a Markdown link by voice** (2026-10-17). "open bracket
  the guide close bracket open paren page close paren" now types
  `[the guide](page)`, with no space in the middle.
- **A backslash in your own phrases is kept** (2026-10-17). A phrase in My
  Words and Phrases that writes a folder or a file name, such as "my folder"
  writing `C:\new\temp`, was saved in a way that read back as `C:`, a new
  line and `ew`, then a tab. It is now saved with each backslash doubled
  (`C:\\new\\temp`) and reads back exactly as you typed it. Phrases you saved
  before keep working as they did; to fix one that already broke, open My
  Words and Phrases, choose the phrase, Edit, and type the folder again.
  Limits: when you edit `dictation.md` by hand, `\n` is still a new line and
  `\t` a tab, so write `\\` for a backslash before those letters.

- **Emoji arrive whole** (2026-10-17). Dictate Anywhere and abbreviations
  that expand everywhere now type an emoji (or any character beyond the first
  65,536 in Unicode) as one character. Before, a plain edit box such as the
  Run box (Windows+R) could receive it without its first half. For example, an
  abbreviation "thx" that expands to "Thanks! 🙏" now types the folded hands
  too, in any program. Some rarer Chinese characters could also be typed as a
  plain Latin letter; fixed as well. Limits: a program whose font has no
  picture for an emoji still shows a box, though the character is there and
  your screen reader reads it by name.

- **Alt+Q opens the QuillVille menu again** (2026-10-17). The **Quick Insert...** button in Inkwell's window also claimed Alt+Q, and Windows gives a letter that a button and a menu share to the button, so Alt+Q opened Quick Insert and the guide's "Alt+Q, then Q to open QUILL" typed a Q into Quick Insert's filter instead. The button is now Alt+I (Quick &Insert), and Alt+Q opens QuillVille, so Alt+Q then Q, R, W, V or T opens QUILL, Quill Radio, Quill Weather, Quill Converter or QUILL Transcribe as section 3 of the guide says. Ctrl+K still opens Quick Insert from the window. Section 9 of the user guide explains the button's letter with an example.
- **No review-first box where there is nothing to review** (2026-10-17). Inkwell's **More Dictation Settings** (from **Dictation > Dictation Settings...**, Ctrl+Alt+D, then **More Dictation Settings...**, Alt+A) no longer shows **Send dictation to review first** (it was Alt+V). That box sends each phrase to the **Review Dictation** window of QUILL, QUILL Lite and QUILL Transcribe instead of typing it; Inkwell has no such window, so Dictate Anywhere always types straight into the program you are in and the box did nothing here. As with the polishing box hidden earlier today, your choice is kept: if you share dictation settings with the family and turned review first on in QUILL, pressing OK in Inkwell's Dictation Settings leaves it on, whichever style you choose. For example: turn it on in QUILL, choose **Verbatim** in Inkwell and press OK, and QUILL still sends your phrases to Review Dictation. To change it, use one of those three programs. The user guide's "Correcting yourself as you talk" part says so, with that example.

- **Which speech engine Dictate Anywhere uses, explained** (2026-10-17). The user guide's section 20 has a new part, "Which speech engine Dictate Anywhere uses": every choice in the Speech engine list, and the plain fact that Inkwell's installer does not include the built-in Moonshine and Whisper models or the speech part that runs them, which downloaded models, OpenAI and speech providers need too. On a computer with only Inkwell, choose Windows speech recognition, or install QUILL Transcribe, which then does the dictating when you press your Dictate Anywhere key. It also covers Better Accuracy: Speech Models (Alt+B), all twelve Speech Providers (Alt+V), consent with No as the default, Spanish (commands stay in English), and a worked example.

- **No polishing box where there is nothing to polish** (2026-10-17). Inkwell's **More Dictation Settings** (from **Dictation > Dictation Settings...**, Ctrl+Alt+D, then **More Dictation Settings...**, Alt+A) no longer shows **Allow polishing my dictation with AI**. Polishing with AI happens only in the **Review Dictation** window of QUILL, QUILL Lite and QUILL Transcribe, where you read the tidied words before anything is inserted, and Inkwell has no such window, so the box did nothing here. Hiding it does not change your choice: if you share dictation settings with the family and turned polishing on in QUILL, saving Inkwell's Dictation Settings leaves it on, even when you choose the **Verbatim** or **Clean** style. Every other box in the window keeps its Alt key. The user guide's "Correcting yourself as you talk" part now says where polishing lives.
- **QUILL Transcribe on the QuillVille menu and the tray** (2026-10-16). QUILL Transcribe, which types what you say into any program, is released on 1 November 2026. Inkwell's **QuillVille** menu lists it last (Alt+Q, then T, or Ctrl+Alt+Shift+F11); QUILL, Quill Radio, Quill Weather and Quill Converter keep F7 to F10. The tray icon's menu adds **Open QUILL Transcribe** after QUILL, Quill Radio and Quill Weather. If it is not installed, Inkwell offers to download it once it is published, and nothing is downloaded until you say yes. The user guide has a new part, "Opening the other QuillVille apps", in section 3.
- **Dictation settings shared with the family** (2026-10-16). With **Share dictation settings with every QuillVille program** checked (Alt+Q, in More Dictation Settings), Dictate Anywhere uses the dictation settings you save in QUILL, QUILL Lite or QUILL Transcribe, and what you save in Inkwell reaches them. The read-back, your key and every permission to send your speech stay Inkwell's own. Your own settings are backed up the first time, and a save that cannot reach the others is said aloud. The word list now lives in `%LOCALAPPDATA%\QuillVille\Dictation`, copied from QUILL's data folder with the old file kept.
- **A big abbreviation list opens and searches at once** (2026-10-16). **Manage Abbreviations** (Ctrl+M) reads its rows only as you reach them, so ten thousand abbreviations fill instantly (it took over three seconds, and again after every key typed in the search box). The search finds words in any order, and the selection stays on the abbreviation you were on when the search changes.

- **Fixing it when you correct yourself** (2026-10-16). With **Fix it when I
  correct myself** (Alt+X) checked in Dictation Settings, "Thursday, no,
  Friday" types Friday: a "no", "I mean", "sorry" or "scratch that word"
  between two days, months, numbers or names from My Words keeps the second.
  Anything else is typed as said, and it is off until you turn it on.
  **Dictation style** (Alt+Y) sets it and filler removal together, as
  Verbatim or Clean. The same as in QUILL, QUILL Lite and QUILL Transcribe.
- **Correcting in Dictate Anywhere** (2026-10-16). "Correct that" and "choose" a number, "capitalize that", "all caps that", "no caps that", "replace" some words "with" new ones, "change that to" and new words, "delete last sentence" and "delete previous paragraph" now work in other programs, on the words dictation typed there itself, by taking them back with Backspace and retyping. Inkwell never reads the other program. A correction is refused, with one sentence and nothing sent, if the focus has moved, if you have typed or clicked since, or, for the commands that retype words, in Word and Outlook. With Moonshine or Whisper, "correct that" asks the other built-in engine to listen again and offers its answer as choice two.
- **Snippet blanks by voice in Dictate Anywhere** (2026-10-16). "insert snippet" and a name now asks for each blank ("Title?") and each choice ("Choose NVDA, JAWS or Narrator."), then types the whole snippet once. Say skip, scratch that to go back one, or cancel to type nothing. "read that" reads back all of what was typed, not just the snippet's name.

- **Speech providers in Dictate Anywhere** (2026-10-16). Dictation Settings has the editors' **Speech Providers...** button (Alt+V), so Dictate Anywhere can use a speech company you already have an account with. Keys go to Windows Credential Manager, and you are asked before anything is sent.

- **Every release build checks its version against what is published** (2026-10-15). The shared QuillVille runtime carries every app's version number, so a build of one app could make another report a version nobody can download yet, and Check for Updates would then never offer the real one. Quill Inkwell's release builds now run the same check Quill Radio, QUILL Lite, QUILL Cast and Quill Weather already did, and a build of every app at once checks them all again instead of stopping at an app it did not know.

- **The command word in Dictate Anywhere** (2026-10-15). Say QUILL before a
  command, "QUILL scratch that", and whatever follows QUILL is never typed; if
  it is not a command you hear "Not a command", and "QUILL type that" types
  it. "QUILL command mode" takes commands without the word until "dictation
  mode" or eight seconds with none. The word, strict mode and the seconds are
  in More Dictation Settings (Alt+C, Alt+E, Alt+D). Two new sounds play when
  QUILL hears the command word and when command mode ends.

- **QUILL Lite's words in Dictate Anywhere** (2026-10-15). Dictate Anywhere
  uses QUILL's My Words and Phrases list, as before. QUILL Lite can now share
  that list (Use the shared word list, in its My Words and Phrases), so the
  names you teach QUILL Lite come out right here too. QUILL, QUILL Lite and
  QUILL Transcribe can also import and export the list.
- **Dictate Anywhere stays in the field you started in** (2026-10-15). If the
  focus moves while you dictate, Inkwell pauses and holds your words instead of
  typing them somewhere else, as QUILL Transcribe does. **Dictation > Resume**
  (Ctrl+R), **Resume in This Field** (Ctrl+Shift+R) and **Discard Held Words**
  (Ctrl+Shift+D), also in the tray menu while paused.
- **Programs dictation never types into** (2026-10-15). A list you keep, in
  More Dictation Settings (Alt+N), that starts with the common password
  managers and the Windows sign-in prompts. Dictation refuses a listed program
  by name and types nothing.

- **Where Quill Inkwell's own sounds play, and Alt+Shift+M to turn them off.** The **App Sounds Play On...** button in **Options > Preferences...** (Ctrl+,) offers System default, None (no sounds), or any sound card or headset by name. After a change one sound plays on the new card, so you hear where it went. If that card is unplugged the sounds play on the system default until it is back, and Quill Inkwell says so once. **Alt+Shift+M** turns Quill Inkwell's sounds off and back on where they were, and **Options > App Sounds** shows a check mark while they are on. Each QUILL app keeps its own choice; "Share these choices with my other Quill apps" keeps them in step. Your screen reader is never moved. Asked for on QUILLVille by Rick Lewis.

- **Dictate Anywhere: one microphone, and your library by voice** (2026-10-13).
  Inkwell takes the family's one microphone lock while it listens, so it never
  dictates at the same time as QUILL, QUILL Lite or QUILL Transcribe, and it
  says which one is when it cannot start. "insert snippet", "insert
  abbreviation" and "paste clip" now work in other programs, typed as one
  phrase that "scratch that" takes back whole (blanks are typed as [name], and
  the cursor stays at the end). Its Dictation Commands list shows only what
  works in other programs.

- **Two downloads, nothing else** (2026-10-11). Quill Inkwell now comes as the
  installer and the portable zip. The small Lite installer and the Companion
  zip are gone. If you used the Lite installer, take the installer; if you
  used the Companion zip, take the portable zip. Check for Updates already
  offers the right one.

- **Dictate Anywhere** (2026-10-05). Inkwell now hosts dictation into other
  programs, with the editors' shared controller, engines, My Words and Phrases
  (`dictation.md` in the shared data folder) and commands
  (`quill/apps/inkwell_dictation.py`, `quill/core/windows_dictation/anywhere.py`,
  `quill/ui/windows_dictation_external.py`). **File > Dictate Anywhere Key...**
  (Ctrl+Alt+Shift+D) chooses the system-wide key, none by default, with the
  same picker and refusals as the other keys. A new **Dictation** menu has
  **Dictate Anywhere** (Ctrl+D, a check item) and **Dictation Settings...**
  (Ctrl+Alt+D), the editors' own window over Inkwell's stored copy. Each phrase
  is typed at the cursor of the program in front; "scratch that" sends
  backspaces only while the same window keeps the focus. Commands that need to
  read the other program's text (select, go to, correct, clips, snippets) are
  answered "That works in QUILL's own documents...". Refused with a sentence:
  password fields, programs running as administrator when Inkwell is not,
  QUILL's own windows (Ctrl+F11 there) and Inkwell's own window. The read-back
  defaults to a tone, since the screen reader echoes typing. An editor's
  **Dictate in Other Programs...** hands its settings over once
  (`dictate-anywhere.json`) and starts Inkwell, opening the key chooser if no
  key is set. Off in Safe Mode.
- **No show and hide key until you choose one** (2026-10-05). The app
  registered Ctrl+Alt+Shift+I system-wide, and other QuillVille apps use that key for
  menu commands, so while this app ran theirs never fired. It now has no key by
  default; **File > Show and Hide Key...** (Ctrl+Alt+Shift+H) lets you type
  one, or leave it empty for none, and refuses a key any QuillVille app uses as
  a command or as its own show and hide key, in one sentence naming the app.
  Somebody who had the old key is moved to none and told once, at the next
  launch; a key somebody chose is kept (`quill/core/family_chords.py`,
  `quill/core/show_hide_keys.py`, `quill/ui/show_hide_key_picker.py`).
- **No Quick Insert or Expand Word key until you choose one** (2026-10-05).
  Ctrl+Alt+Shift+K (Quick Insert) and Ctrl+Alt+Shift+X (expand the word just
  typed) were registered system-wide too, and both are commands elsewhere in
  the family -- X is Quill Radio's Export My Setup -- so they went the same way.
  **File > Quick Insert Key...** (Ctrl+Alt+Shift+K) and **File > Expand Word
  Key...** (Ctrl+Alt+Shift+E) use the same picker and the same refusals, and
  also refuse a key Inkwell already uses for one of its other two. Somebody
  still on the old keys is moved to none and told once in one sentence; a key
  somebody chose is kept (`quill/apps/inkwell_keys.py`,
  `InkwellSettings.take_system_keys`).

## 1.0.0 -- 2026-08-11

First release. Abbreviation expansion in every Windows application, sharing one
library with QUILL.

### Added

- **An application icon of its own.** This was the single hard blocker on
  cutting the 1.0.0 build, which is why it is recorded here rather than as a
  fix after the fact. The icon the app was scaffolded with was a byte-identical
  copy of Quill Weather's -- which was itself a copy of Quill Radio's -- so a
  listener with more than one QuillVille app installed would have seen the same
  face for several different products in the taskbar, in Alt+Tab and in the
  tray. For a tray-resident app like Inkwell, the tray is where it lives its
  whole life.

  Inkwell's icon is a gold nib dipped into a white inkwell, on a terracotta
  tile: the app is named for the well, and the pot is a silhouette nothing else
  in the family has. It shares the family's rounded tile shape and gold accent,
  and differs from every sibling in picture and in colour. Two alternatives were
  drawn and rejected for failing at 16x16, which is the size that actually
  matters -- expanding text lines blurred to a grey block, and a bare fountain
  nib read as a flame.

- **System-wide expansion.** A low-level keyboard hook recognises an
  abbreviation as you finish typing it and replaces it in whatever application
  has focus. Expansions are typed as synthesised keystrokes and never touch the
  clipboard.
- **One shared library.** Inkwell and QUILL read and write the same
  `abbreviations.json`. An abbreviation added in either app works in both, with
  no import or sync; the file is re-read whenever it changes on disk.
- **Per-abbreviation settings.** Each entry carries its own category, trigger
  mode (a space or punctuation, a space only, punctuation only, or never), speech
  mode, sound override, trailing-space behaviour, and case sensitivity. Schema
  version 2, backward and forward compatible.
- **Quick Insert.** A type-to-filter picker over every enabled abbreviation,
  ordered by how often each is used, reachable from the window (Ctrl+K) or from
  anywhere (Ctrl+Alt+Shift+K). The only way to reach an entry whose trigger mode
  is Never.
- **New from Clipboard.** Ctrl+Shift+N turns whatever is on the clipboard into a
  new abbreviation, pre-filled.
- **Fill-in fields.** `${field:Label}` and `${field:Label=default}` make an
  expansion ask before it finishes; a label used twice is asked once and filled
  everywhere. The form is the same one QUILL's editor uses, so a template
  behaves identically in both.
- **Categories** with a filter in the manager, and a category column in both
  lists.
- **Variables** in expansions: `${date}`, `${time}`, `${datetime}`, `${day}`,
  `${month}`, `${year}`, `${username}`, `${clipboard}`, `${cursor}`.
- **Case preservation.** `Btw` capitalises and `BTW` shouts, for entries that
  are not case sensitive.
- **Exclusions.** Password managers, the Windows sign-in and lock surfaces, the
  credential prompt, and the UAC dialog are permanently excluded, plus any
  applications the user adds.
- **Paste fallback** for the few applications that drop synthetic keystrokes;
  the previous clipboard contents are always restored.
- **Tray residence**, start-with-Windows, start-minimized, and a close button
  that keeps expansion running.
- **Safe Mode support.** `QUILL_SAFE_MODE=1` prevents the keyboard hook from
  being installed at all.

### Working everywhere you can type

- **Expands only where text is accepted.** Before replacing anything, Inkwell
  checks that the focused element takes text, so backspaces never land in a list
  doing type-ahead or a page where Backspace means "go back". Where it cannot
  tell, it goes ahead -- a missed expansion is the more annoying failure.
- **AltGr characters no longer break expansion.** Windows reports AltGr as
  Ctrl+Alt, and treating that as a command wiped the buffer mid-word on every
  layout that uses it -- German, Polish, Spanish, Portuguese, the Nordic
  layouts. AltGr is now recognised as typing.
- **Backspace immediately after an expansion takes it back**, restoring the
  abbreviation. The offer lasts a few seconds and only in the window where the
  expansion happened.
- **Expand on demand** with Ctrl+Alt+Shift+X (or the Abbreviations menu): expands
  the word before the cursor without waiting for a space or punctuation, so it
  works mid-word, at the end of a line, and for entries set never to expand on
  their own.
- **Quick Insert from anywhere** with Ctrl+Alt+Shift+K.
- **Per-application delivery.** The clipboard-paste route can be turned on for
  one stubborn program (`paste_processes` in `inkwell.json`) instead of globally,
  so no other application has its clipboard borrowed.
- **The hook repairs itself.** Windows silently removes a keyboard hook that
  responds too slowly; Inkwell re-installs its own every few minutes so expansion
  cannot quietly die for the rest of a session.
- **One expander per window.** QUILL's editor expands from the document itself,
  so Inkwell stays out of it rather than expanding the same word a second time.
  QUILL marks its own window; the marker identifies the actual window, so a
  development run and a renamed build are covered alike.
- **Elevated windows are explained, not silently broken.** A normal-privilege
  program cannot see keys typed into an administrator window, so Inkwell says so
  the first time focus lands in one.

### Notes

- Inkwell keeps no clipboard history, by design.
- The keystroke buffer is bounded at 64 characters, held in memory only, cleared
  constantly, and never written anywhere. See the user guide's Privacy section
  and the PRD's security contract.
