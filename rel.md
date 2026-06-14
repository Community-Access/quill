# QUILL 0.6.0 release notes

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

Open a source file and QUILL loads a *language profile* from the file extension — Python, JavaScript and TypeScript, Kotlin, Shell, Markdown, JSON, TOML, and SQL are recognised, with a sensible plain-text fallback.

- **Move by token.** **Next Token** and **Previous Token** (in the Navigate menu) jump the caret to the next identifier, keyword, operator, or literal, which is far more predictable than word movement when you are reading code by ear.
- **Set the language yourself.** **Navigate → Set Document Language** overrides the automatic choice — handy for an unsaved buffer, an unusual extension, or a snippet pasted into a plain file.

Paired with indentation tones, code-aware editing lets structure come through as pitch while you move through the meaning token by token.

## New: text encoding tools

If you have ever fought a file that was UTF-8 when the next tool wanted plain ASCII, these three commands under **Format → HTML & Encoding** are for you.

- **Show Non-ASCII Characters** opens a read-only report of every character beyond plain ASCII — with its line and column, codepoint, name, and whether it converts cleanly to Latin-1 and Windows-1252 (MS-ANSI). Reviewing that list with your screen reader replaces the old trick of running a file through `iconv` with a sentinel string and hunting for what failed.
- **Convert Non-ASCII to HTML Entities** rewrites every accented letter or symbol as an HTML entity (`&eacute;`, or `&#233;` when there is no name), while leaving ordinary text and existing markup alone. This is the reliable way to feed text to a tool — Pandoc is the classic example — that refuses anything with high characters in it.
- **Re-encode As...** saves a copy in the encoding you choose (UTF-8, UTF-8 with a byte-order mark, Latin-1, Windows-1252, or ASCII). Anything that does not fit a narrow target is written as a numeric HTML entity instead of a silent question mark, so nothing is quietly lost.

**Why it matters.** This turns a fiddly, error-prone command-line ritual into three clear, screen-reader-friendly menu commands — and the "nothing is lost" guarantee means you can convert with confidence.

## Smaller additions worth knowing

- **Speak where you are.** From the QUILL key, press **F** to speak the window title, **P** to speak the full file path, or **Q** to speak a short status summary — without leaving the editor.
- **Launch straight to the spot.** `--goto FILE:LINE:COL` opens a file at a position in one argument (great when a linter or search result hands you a `file:line:column` string), and `--diff LEFT RIGHT` opens two files straight into compare mode.
- **A friendlier bug report.** **Help → Report a Bug...** now opens focused on the Summary field, remembers your name and email so you only type them once, and asks which screen reader you use (pre-selected from what QUILL detects) so the team can reproduce reader-specific issues.
- **More file types in Open**, including common developer extensions (Kotlin, TypeScript, Go, Rust, and more), and **HEIC/HEIF images** are now supported for AI image description.
- **The About screen** now credits every GitHub contributor, including new project owner Kelly Ford and design contributor Ken Perry.

## Fixes that change the day-to-day

- **Describe Image works again.** A small internal error was silently stopping the "Describe Image with AI" feature from running. It now completes as intended — the impact is that an accessibility feature blind users rely on is dependable again.
- **macOS keeps your API keys.** On macOS, your AI provider keys and tokens are now stored in the login Keychain instead of being lost between sessions, so you set them up once. The broader impact is that on-device and cloud AI "just work" after the first setup.
- **A steadier preview.** If the Windows WebView2 control faults, QUILL now catches the error and quietly rebuilds the preview instead of letting the side preview crash — so a flaky browser component no longer interrupts your writing.
- **macOS builds install cleanly.** The notarized macOS build now signs its bundled image libraries and uses hardened-runtime entitlements, fixing notarization so the app installs without security warnings.

## Things that work a little differently now

- **Two entity commands, two jobs.** The older **Encode HTML Entities** still escapes only the five markup characters (`<`, `>`, `&`, `"`, `'`). The new **Convert Non-ASCII to HTML Entities** is the one that handles accents and symbols. If you used to reach for the old command expecting it to fix accented text for Pandoc, reach for the new one instead.
- **Sound is opt-in.** Most earcons are off until you choose a sound pack and enable events, so nothing about your current setup gets noisier on upgrade. Turn sound on from **Preferences → Sound** and **Tools → Reading & Dictation → Sound Events...**.
- **Indentation tones default to Off.** They only play once you pick a scale, so code files stay silent unless you ask for the tones.
