# QUILL 0.5.1 release notes

This release is about feedback you can hear, comparisons you can move through by keyboard, smarter handling of code, and a set of practical encoding tools for anyone who prepares text for the web. Everything below is built screen-reader-first: sound is always optional and never replaces speech, and every new view is a real, navigable control rather than a visual-only flourish.

If you are upgrading from 0.5.0, the "Things that work a little differently now" section near the end lists the few places where a habit or a menu location changed.

## New: sound notifications you can shape

QUILL can now play short, non-speech audio cues — earcons — at meaningful moments: a file saved, a search found, a comparison opened. The point is to let your screen reader stay focused on the text while a quick sound carries the "something happened" signal.

- **What it is.** Sounds come from a *sound pack*: a folder (or a single `.qsp` file) of audio clips with a small manifest that says which event plays which sound. QUILL ships a pack called **Ink**, and you can drop in your own.
- **You are in control.** Open **Tools → Reading & Dictation → Sound Events...** to switch individual events on or off. They are grouped — Earcons, Compare, and Indentation tones — so you can keep the cues you like and silence the rest. **Toggle Sound Notifications** turns everything on or off at once and plays a short "on" or "off" cue so you know where you landed.
- **Why it matters.** For a screen-reader user, a well-chosen sound is faster than a spoken phrase and never talks over your reader. Because it is all opt-in and per-event, it adds information without adding noise.

### Indentation tones for code

When you turn on indentation tones (pick a musical scale under the **Indentation tones** setting, or leave it Off), QUILL plays a pitch that rises as your caret moves deeper into indented code and falls as you come back out. Blank lines stay silent and hold the last level, so cursoring through gaps does not chirp. It is a quiet, ambient way to feel the shape of code without counting spaces.

## New: compare mode you can navigate by ear

Comparing two files is now a first-class, keyboard-driven experience. Open a comparison and move through it with **F8** (next difference), **Shift+F8** (previous), **Ctrl+F8** (re-announce the current one), and **Alt+F8** (hear just the words that changed on a line). The differences are presented as a real list you can review one at a time with your screen reader.

If you use a sound pack, compare mode also gives you distinct cues for opening and closing a comparison, stepping between differences, and bumping against the first or last one — so you can keep your attention on the text and let sound tell you where you are.

**Why it matters.** Reviewing edits used to mean a lot of careful re-reading. Now you can step difference-to-difference at the speed you read, with both speech and optional sound confirming each move.

## New: code-aware editing

Open a source file and QUILL loads a *language profile* from the file extension — Python, JavaScript and TypeScript, Kotlin, Shell, Markdown, JSON, TOML, and SQL are recognized, with a sensible plain-text fallback.

- **Move by token.** **Next Token** and **Previous Token** (in the Navigate menu) jump the caret to the next identifier, keyword, operator, or literal, which is far more predictable than word movement when you are reading code by ear.
- **Set the language yourself.** **Navigate → Set Document Language** overrides the automatic choice — handy for an unsaved buffer, an unusual extension, or a snippet pasted into a plain file.

Paired with indentation tones, code-aware editing lets structure come through as pitch while you move through the meaning token by token.

## New: text encoding tools

If you have ever fought a file that was UTF-8 when the next tool wanted plain ASCII, these three commands under **Format → HTML & Encoding** are for you.

- **Show Non-ASCII Characters** opens a read-only report of every character beyond plain ASCII — with its line and column, codepoint, name, and whether it converts cleanly to Latin-1 and Windows-1252 (MS-ANSI). Reviewing that list with your screen reader replaces the old trick of running a file through `iconv` with a sentinel string and hunting for what failed.
- **Convert Non-ASCII to HTML Entities** rewrites every accented letter or symbol as an HTML entity (`&eacute;`, or `&#233;` when there is no name), while leaving ordinary text and existing markup alone. This is the reliable way to feed text to a tool — Pandoc is the classic example — that refuses anything with high characters in it.
- **Re-encode As...** saves a copy in the encoding you choose (UTF-8, UTF-8 with a byte-order mark, Latin-1, Windows-1252, or ASCII). Anything that does not fit a narrow target is written as a numeric HTML entity instead of a silent question mark, so nothing is quietly lost.

**Why it matters.** This turns a fiddly, error-prone command-line ritual into three clear, screen-reader-friendly menu commands — and the "nothing is lost" guarantee means you can convert with confidence.

## New: hand it over in Word (or RTF)

Sooner or later somebody asks for "the Word version." Now you can just give it to them. **File -> Save As...**, pick **Word Document (*.docx)** (or Rich Text) from the type list, and QUILL converts your document on the way out the door — no copy-paste-into-Word dance, no reformatting marathon.

And because we hand the conversion to Pandoc with real Word styles, your headings come out as actual Word headings, not "bold text that looks like a heading." That means the file is navigable by the next person's screen reader too — accessibility doesn't stop at the export button.

A word to the wise: Word keeps whatever structure your source had. Save a richly formatted Markdown or HTML document and it arrives dressed for the occasion; save a plain-text file and you get a tidy but unadorned document, because there was no structure to carry. QUILL will tell you so rather than quietly flattening your work.

## New: citations without the tears

Setting up MLA or Chicago citations has a special talent for going wrong at 2 a.m. the night before a paper is due — a comma in the wrong place, an italic that should not be there, a hanging indent that refuses to hang. QUILL now does the fussy part for you.

**Insert -> Insert Citation...** opens a plain, labelled form: pick your source type (book, journal article, or website), pick your style (MLA 9, Chicago 17, or APA 7), type in what you know — author, title, year, the usual suspects — and choose whether you want the in-text citation, the full bibliography entry, or both. QUILL formats it correctly and drops it in at your cursor.

You provide the facts; QUILL handles the punctuation gymnastics. The goal here is simple and, frankly, a little bit personal for an accessibility-first editor: a screen-reader user should never be at a disadvantage just because citation formatting is finicky visual busywork. Now you are on the same footing as everyone else in the seminar — and you got there without fighting a single hanging indent.

## Smaller additions worth knowing

- **Speak where you are.** From the QUILL key, press **F** to speak the window title, **P** to speak the full file path, or **Q** to speak a short status summary — without leaving the editor.
- **Switch documents with Ctrl+Tab** (and Ctrl+Shift+Tab to go back), the shortcut your fingers already expect.
- **Files open where you work.** Open and Save As now start in your Documents folder, and you can set your own default startup folder in Preferences — no more landing in the install directory.
- **Launch straight to the spot.** `--goto FILE:LINE:COL` opens a file at a position in one argument (great when a linter or search result hands you a `file:line:column` string), and `--diff LEFT RIGHT` opens two files straight into compare mode.
- **A friendlier bug report.** **Help → Report a Bug...** now opens focused on the Summary field, remembers your name and email so you only type them once, and asks which screen reader you use (pre-selected from what QUILL detects) so the team can reproduce reader-specific issues.
- **Feature search finds more.** Searching the feature list now returns copy tray, macros, and abbreviations.
- **More file types in Open**, including common developer extensions (Kotlin, TypeScript, Go, Rust, and more), and **HEIC/HEIF images** are now supported for AI image description.
- **The About screen** now credits every GitHub contributor, including new project owner Kelly Ford and design contributor Ken Perry.

## Fixes that change the day-to-day

This release also clears out a batch of accessibility and startup problems that got in the way day to day.

- **Report a Bug actually accepts typing now.** Under NVDA, the bug-report fields were refusing keyboard input. The dialog has been rebuilt so every field is editable, and it moved to the Help menu where you would expect it. It also no longer freezes the app while it contacts the server — that work happens in the background with a timeout. The impact: reporting a problem is no longer itself a problem.
- **JAWS stops saying "splitter window" and "panel."** Those stray announcements on menu close and when the app took focus are gone, because the invisible layout container is no longer exposed to your screen reader. Quieter focus changes mean less to wade through.
- **Describe Image works again.** A small internal error was silently stopping the "Describe Image with AI" feature from running. It now completes as intended — an accessibility feature blind users rely on is dependable again.
- **Faster, quieter startup.** Screen-reader detection now runs in the background instead of stalling the first window, a crash in the preview warm-up is fixed, and the title bar no longer flashes "untitled Quill unavailable" before the app is ready. The preview pane also no longer hangs for minutes with no way to close it.
- **A reliable first run.** The first window now comes to the foreground so the trust and privacy dialog is reachable, and you can re-open the personalization wizard later if you skipped it. The wizard's startup beep and its Cancel-button focus are fixed too.
- **A tidier Personalize Quill wizard.** Two snags in the setup wizard are gone: the "Play sounds for mode changes" checkbox on step 2 now reads with its label instead of as an unlabeled control, and the profile choices on step 3 now wrap when you arrow past the last one instead of dumping you onto the Back and Next buttons.
- **Quill actually quits now.** When running from source, Quill could refuse to close — the window would shut but the process kept running until you killed it from the console. A stray background window was holding the door open; it now gets cleaned up on exit, so closing the window closes Quill.
- **The user guide opens the right way.** It now opens as a read-only page in your browser instead of as an editable Markdown document you could accidentally change — and a stray edit can no longer throw a `0x8007139f` browser error. A glossary of QUILL terms was added to the guide as well.
- **macOS keeps your API keys.** Saving an Ask Quill API key on macOS used to crash; keys and tokens are now stored in the login Keychain, so you set them up once and on-device or cloud AI just works.
- **macOS builds install cleanly.** The notarized macOS build now signs its bundled image libraries and uses hardened-runtime entitlements, so the app installs without security warnings.

## Things that work a little differently now

- **Two entity commands, two jobs.** The older **Encode HTML Entities** still escapes only the five markup characters (`<`, `>`, `&`, `"`, `'`). The new **Convert Non-ASCII to HTML Entities** is the one that handles accents and symbols. If you used to reach for the old command expecting it to fix accented text for Pandoc, reach for the new one instead.
- **Sound is opt-in.** Most earcons are off until you choose a sound pack and enable events, so nothing about your current setup gets noisier on upgrade. Turn sound on from **Preferences → Sound** and **Tools → Reading & Dictation → Sound Events...**.
- **Indentation tones default to Off.** They only play once you pick a scale, so code files stay silent unless you ask for the tones.
