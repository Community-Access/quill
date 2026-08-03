# QUILL Audio Studio 1.0.0 - Release Notes

Released 2026-07-18.

Introducing QUILL Audio Studio: the QUILL editor's audiobook and audio production suite as its own standalone Windows and macOS desktop app - screen-reader-first, keyboard-first, and spoken end to end. It is for anyone who wants to turn writing into finished, chaptered, publishable audio without ever touching a waveform display - and then to sit back and listen to it.

> These are the notes for the first release. Everything that has landed since - the shared QuillVille Runtime and the lighter downloads it makes possible, the arrow-navigable status bar, the audio converter, and announcements in braille - is in the 2.2.0 notes, `release-notes-2.2.md`.

## What it is

One small home window, three journeys:

- **Narrate Documents** - a folder of Word, Markdown, HTML, or text files becomes speech audio or a single chaptered audiobook, read by any voice you choose - or by a whole cast.
- **Build From Recordings** - a folder of recordings becomes one chaptered master, each file a chapter, with a review step before the merge.
- **Edit a Book** - the Chapter Workbench opens any chaptered MP3 or M4B (or a chapterless recording, as one chapter ready to carve): a chapter-aware player, split-at-playhead chapter surgery, tags and cover, AI-proposed titles, an ACX compliance check, and publishing.

## Headline features

- **A guided wizard that asks one thing at a time.** Every step announced ("Step 2 of 7: What should I read?"), Back/Next/Skip to summary, validation in plain language, and a plain-sentence review before Start. The wizard remembers your last journey, your recent source folders, and your recent books.
- **Voices from every era.** Windows SAPI 5, DECtalk, Piper and Kokoro (neural, fully offline), eSpeak-NG, and the macOS system voice; ElevenLabs and the OpenAI/Gemini/ElevenLabs multilingual cloud voices with your own API key. Engines, voices, and models download on demand from the Voices menu; every voice has a comparable preview.
- **A cast, not just a voice.** Round-robin rotation, glob-based voice casting rules ("*interview* = the guest voice"), and translated editions in additional languages via your AI provider or local LibreTranslate.
- **Honest, resumable runs.** Audition mode (first document only), dry run (proofread the exact spoken text), incremental rebuilds (only changed documents re-synthesize), spoken progress milestones at 25/50/75 percent, and `.quilljob` files that pin an entire run for one-keystroke repeats.
- **Chapter surgery by ear.** Split at playhead, set start to playhead, merge, rename, restore; silence-based chapter proposals; AI title proposals (chapter openings transcribed locally, only text sent to your AI, everything reviewable); chapter list import/export in five formats; split a book back into per-chapter files.
- **Publishing without a browser.** A local RSS podcast feed, a whole-folder show feed with accessible show notes, SFTP upload with credentials in the Windows Credential Manager, and Auphonic mastering in your own account - each an explicit, consented action with spoken progress and a real Cancel.
- **ACX compliance in plain words.** Loudness, true peak, and noise floor measured against Audible's window, with a concrete recommendation per failing criterion - from the Book Tools menu for any file, or one button in the Workbench.
- **A library that organizes itself.** Your books live in a tree on the home window - Favorites, In Progress, Recently Played, and Inbox, plus any folders you make - that fills in as you open books, with a keyboard-complete context menu (Open, Reveal in Folder, Favorite, Move to Folder, New Folder, Remove). Reveal in Folder shows the file in your OS file manager; Remove only drops it from the list.
- **A studio you can listen in.** Resume where you left off on launch (opt-in), a Recently Played submenu, media keys that drive the active player from any window, per-book volume and mute (Ctrl+M) that each book remembers, a Sleep Timer that stops after the minutes you choose or at the end of the current chapter, and a Play Queue that opens the next book for you when one finishes.
- **A desk that stays out of the way.** System tray with Resume-last-book, opt-in Alt+F4-to-tray, a close policy that only asks when real work would be lost, Ctrl+Shift+P command palette (the journeys, publishing, the ACX check, the Speech Hub, downloads, and the sleep timer, mute, and play-queue commands), and in-app update checks that download the right artifact for your flavor.
- **Safe Mode.** `QUILL_SAFE_MODE=1` or `--safe-mode` disables AI, publishing, and downloads while everything local keeps working.

## Relationship to QUILL

The Studio runs the exact same Audio Studio code that ships inside the QUILL editor - carried here as a self-contained copy - and shares QUILL's data store (`%APPDATA%\Quill`, or the portable `data` folder). Voices, downloaded engines, speech settings, your book list, and listening positions are one set of data across QUILL, QUILL Audio Studio, Quill Radio, and QUILL Cast. You do not need QUILL installed to use the Studio, and nothing you set up in one app is stranded in the other.

## Editions

Two downloads shipped with this release: an installer that puts the Studio in its own folder with a Start Menu group and an uninstaller, and a portable zip you extract anywhere - a USB stick included - where a `data` folder next to the program keeps every setting, voice, and book position inside the app folder so the whole studio travels with you. Both bundle ffmpeg and the mpv player engine. You can also run it from a source checkout.

The lighter, shared-runtime editions arrived after this release; see the 2.2.0 notes.

## Known limitations

- **Windows-first; macOS supported.** The macOS build narrates with the system voice (plus Piper, Kokoro, and eSpeak-NG) and plays previews through `afplay`. Windows-only pieces degrade gracefully elsewhere: SAPI 5 and DECtalk are Windows engines, and stored secrets (SFTP passwords, the Auphonic token, the ElevenLabs key) use the Windows Credential Manager - on other platforms those fields work per-session but are not persisted.
- **Releases are not code-signed.** Windows SmartScreen warns on first run; choose "More info" then "Run anyway".
- **M4B books save as a new file.** Chapter atoms cannot be rewritten in place; the Workbench's Save As performs a lossless re-mux instead. MP3 books do save in place (tags only).
- **Dev runs show a generic tray/window icon.** The proper app icon is embedded in the packaged exe; running from source falls back to a stock system icon.
- **Cloud features need your own keys.** Cloud translation voices without a configured key are skipped with a note rather than stopping the run; Auphonic and ElevenLabs require your own accounts.
- **ffmpeg does the heavy lifting.** Compressed formats, book assembly, the ACX check, and silence detection all need it. Both packaged flavors bundle it; source checkouts can fetch it with Voices > Get FFmpeg.
