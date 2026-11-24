# FUX-02: carrying the work between apps, with the reason

**Date:** 2026-11-24
**Feature:** FUX-02, "Carry the work between apps, including the reason", from the family UX plan (read it with `git show b7c6a1a04^:complete2.md`). It is held to [family-interaction-contracts.md](family-interaction-contracts.md).
**Decisions it follows:** [2026-11-19-family-ux-pilots.md](2026-11-19-family-ux-pilots.md), section 3. The one cross-app journey is A: from QUILL Cast to a saved place to QUILL. It uses the handoff the family already has (the app launcher and session restore), and no new kind of handoff is added before it works. Beacon takes part only once it is released.
**Out of scope:** Earshot and the macOS apps.

The moment: "Open that transcript in QUILL", or "Transcribe this part of my recording". A handoff should say what it carried, where the new thing is, and how to get back. When the other app is not there, it should say so in a plain sentence and keep the work.

## 1. The existing mechanism, reused

- **The launcher:** `quill/core/app_launcher.py` has `launch_app(key, extra_args=...)`. It finds a sibling app in the shared runtime, beside the current app, or in an adjacent portable folder. It returns False, and never raises, when the sibling is not installed. `is_app_released` is the release gate, and each caller checks it.
- **Opening a sibling or offering to install it:** `try_open_or_offer` in `quill/ui/companion_offer.py`.
- **Opening a file in an editor:** `open_in_editor` in `quill/ui/scribe_app_host.py`. It tries QUILL, then QUILL Lite. It now takes a line and passes it to QUILL as `--line`, which QUILL already accepted and forwards to a running copy.
- **Forwarding to a running QUILL:** `quill/core/ipc.py`. A request carries the path, line, column and action.
- **Session restore** brings each app back to where it was. Cast's bookmarks (`quill/core/media/bookmarks.py`, shared with Radio) keep a position to the millisecond, with a note. Go There returns to that position.

No new handoff type, protocol or "from" argument is added. Where a handoff makes a copy, the copy itself says where it came from, because a document outlives the window that made it.

**Three kinds of handoff** (the first acceptance item):

- **A reference:** an existing file's path is handed to another app, and nothing is copied. Examples are Scribe's Next Steps, a WordPress draft and Explorer's Send To.
- **A copy:** text is written as a new document. The only example is Cast and Radio show notes or transcripts going to QUILL (section 3). The copy goes into the app's own folder in Documents, and the original is untouched.
- **A transformed output:** a Scribe, Converter or Studio result, kept in that app's output folder.

## 2. Every handoff

**Says origin** means the receiving app, or the carried document, names where the work came from. **Missing** is what happens when the other app is not installed, or not released in this build.

| # | From, command | Carries | Receiver | Says origin, way back | Missing or unreleased | Speech | Gap, and fix |
|---|---|---|---|---|---|---|---|
| 1 | Any app: the QuillVille menu and the tray's Open (`_launch_sibling`) | Nothing | A new process, or the running one comes forward | n/a | An install offer, or "... could not be opened; it may not be installed." Unreleased apps are hidden | "Opening {app}." once | None |
| 2 | QUILL Cast: the Transcript window's Open in QUILL (`transcript_reader.py`) | Was: plain text, with no timings | Was: **the clipboard** | Was: no | n/a | Was: "Show notes copied to clipboard" for a transcript | **Fixed (journey A):** saved as Markdown in Documents\QUILL Cast. It names the episode, the show, the app and the moment, lists this episode's bookmarks and their notes, and says how to get back. QUILL opens it with the cursor on the line you were reading. Section 3 |
| 3 | QUILL Cast: an episode's Open Transcript in Editor (`transcript_actions.open_in_editor`) | Was: plain text | Was: the clipboard | Was: no | n/a | Was: "Fetching transcript...", then "Show notes copied to clipboard" | **Fixed:** as row 2, without the moment, because nothing is being read |
| 4 | QUILL Cast: the Show Notes window's Send to Editor, and the episode menu's Send Show Notes to Editor | Was: plain text | Was: the clipboard | Was: no | n/a | Was: two sentences, and the second was false ("Show notes copied to clipboard", then "Sent show notes to a new document") | **Fixed:** saved and opened as row 2, as "Show - Episode show notes.md". One sentence |
| 5 | QUILL, the same podcast commands (`main_frame_podcast_dialogs.py`) | Text, into a new unsaved document | The same process | Was: no | n/a | Was: two ("Opened podcast show notes", then "Sent show notes...") | **Fixed:** the new document starts with the episode, the show and "Show notes, from QUILL." One sentence |
| 6 | Quill Radio: the transcript window's Open in QUILL (`radio/transcript_command.py`, `browse_transcript.py`) | Nothing | Nothing | n/a | The button was **always dimmed**, because its host method was never written | None | **Fixed:** as row 2, saved in Documents\Quill Radio |
| 7 | QUILL Transcribe: a file transcript's Open in QUILL (`transcribe_files.py`, through `AppShell.open_in_quill`) | The path of an app-data copy named by an ID | A new QUILL process | No | Only an error box if the process cannot start. No check that QUILL is there | **None** | Planned (second pull request) |
| 8 | QUILL Studio: picture descriptions, and AI Narrate a Recording (`studio_picture_run.py`, `studio_ai_narrative.py`) | A document written beside the source and named first | `AppShell.open_in_quill` | The document names its source | As row 7 | One sentence, before QUILL comes forward | Studio is not released. Left with row 7's fix to `open_in_quill` |
| 9 | Scribe's Next Steps in Converter, Studio, Player, Cast, Beacon and Social: Open in QUILL (Word) and the like (`scribe_app_host.py`) | The result's path (a reference) | `launch_app("quill")`, else QUILL Lite | No | Hidden when no editor is installed. Otherwise "{editor} could not be opened. {file} is saved in its folder." | Open Result: "Word is open in QUILL" | None. The result lives in your Scribe output folder, and its sentence says so |
| 10 | Scribe: Send to Media Player (MP3, DAISY) in Converter, QUILL and QUILL Lite (`scribe_entry.send_to_player`) | The path | `launch_app("player")` | No | **Offered in public builds, where Media Player is not released**. Choosing it says "Media Player could not be opened..." | As row 9 | Planned (third pull request): offered only where Media Player is released |
| 11 | QUILL Lite: Open QUILL Studio (`lite_window_tools.py`) | Nothing | `launch_app("studio")` | n/a | Hidden when unreleased. Otherwise "QUILL Studio could not be opened; it may not be installed." | "Opening QUILL Studio." | None |
| 12 | WordPress, from the apps that are not editors: open a local draft (`wordpress_family.py`) | The draft's path | `launch_app("quill")` | No | "The draft is waiting in QUILL and QUILL Lite, under File, WordPress, Open Local Draft." | None from the sender | None. The draft stays in the WordPress drafts folder |
| 13 | WordPress player: Open in Player (`wordpress_player_commands.py`) | The stream URL | `launch_app("player")` | n/a | "...is not part of this release yet. Use Open in Browser." or "...not installed beside this app. Use Open in Browser instead." | "Opening {title} in Quill Media Player." | None |
| 14 | Explorer's Convert with Quill verb (`__main__.py`) | Paths | `launch_app("converter")` | n/a | **Silent**: the result was ignored, and QUILL exited | None | Planned (second pull request) |
| 15 | Explorer's Send To, and the scribe, ocr and read actions (`shell_integration.py`, IPC) | Path and action | A running QUILL, or a new one | n/a (it is Explorer) | n/a | The Convert window, or "...is waiting until you close {title}." | None |
| 16 | QUILL Cast: QUILL Lineups, Send to Radio (`lineups_host.py`) | A request file and IPC | `_launch_sibling("radio")` | Radio says what it plays | The install offer, **and still** "Sent ... to Quill Radio to play." | Two sentences | Planned (second pull request) |
| 17 | Quill Radio: an episode's Play Next in QUILL Cast, Add to QUILL Cast Queue and Send to the QUILL Cast Inbox (`cast_handoff.py`) | An entry in `radio-actions.json`, applied when Cast next starts | No launch | Cast applies it quietly | **Offered in public builds, where Cast is not released**, with a confirmation such as "It will be next in the QUILL Cast queue." | That sentence | Planned (third pull request): offered only where Cast is released |
| 18 | QUILL: Dictate in Other Programs (`windows_dictation_extras.py`) | A settings file and `--dictate-anywhere` | Transcribe, else Inkwell | "...has your dictation settings" | "Quill Inkwell is not installed with this copy..." | One sentence | None |
| 19 | Cast and Radio: Edit > Dictate Here (`dictate_here.py`) | The field's place (window, process and control), with `--dictate-here-place` | Transcribe | Transcribe starts only in that field | "Dictate Here needs QUILL Transcribe, which is not installed with this copy." | "Starting QUILL Transcribe. Dictation starts here when it is ready." | None. FUX-07 settled the target |
| 20 | QUILL: Open the Media Player (`main_frame_media_player.py`) | Nothing | `try_open_or_offer` | n/a | Not registered when unreleased | "Opening Quill Media Player." | None |
| 21 | Beacon: open a place that is a Scribe document, or any other file (`beacon/scribe_ui.py`) | The path | An editor, Media Player, the browser, or Windows' own program for the file | No | A file with no program to open it raised an exception through `os.startfile` | "Opened {title}" | Beacon is not released. Left until it is (pilot decision) |

**Not found:** Radio recordings are not handed to Studio or Converter. The Recordings window offers Open in Folder. Converter does not hand its own outputs to Media Player, except through Scribe (row 10). Both are new handoffs, and the pilot decision rules them out until journey A works.

## 3. Journey A, as built

1. **Hear a passage and save the place.** This already existed. Add Bookmark in QUILL Cast (and in Quill Radio, into the same file) keeps the position to the millisecond. Edit Note adds a short note.
2. **Come back later.** This already existed. Session restore reopens Cast where it was, and Bookmarks' Go There, or Enter, starts the episode at the saved moment.
3. **Open the transcript or notes in QUILL without losing where it came from.** This is new:
   - **Open in QUILL** in the Transcript window, or **Open Transcript in Editor** on the episode, writes the transcript as Markdown. It uses the same shape as Save As, with your Speakers or Timestamps choice. The document starts with the episode, the show and this line: "Sent from QUILL Cast at 12:30 in the audio. To hear any line again, play it in QUILL Cast, open its transcript and press Enter on that line." Under the heading **Your bookmarks** it lists each bookmark in this episode by time, with its note. The heading **Transcript** is always there, so heading navigation reaches it. A caption that spans two lines is counted as two, so the cursor still lands on the right line. QUILL opens it with the cursor on the line the Transcript window's cursor was on.
   - **Send to Editor** writes the show notes the same way, headed "Show notes, from QUILL Cast."
   - **Where the file goes:** the copy is written to Documents\QUILL Cast (Documents\Quill Radio for Radio). It is named like Save As names it, "Show - Episode.md". Sending the same thing again reopens that copy. A different document under the same name, such as an edited copy or another show's "Episode 1", gets "(2)" and is never written over.
   - **What is said:** one short sentence, before QUILL comes forward, that leads with the folder: "Saved in Documents, in the QUILL Cast folder. Opening it in QUILL." QUILL's window title, read when it comes forward, names the file. A longer sentence would be cut off at that point. Sending the same document again says "Already saved...". Cast lets the QUILL that answers take the foreground (`AllowSetForegroundWindow`). Without that, a QUILL that is already running would only flash on the taskbar. With no QUILL, it opens in QUILL Lite, which has no line option, so the sentence adds "It opens at the top." With neither editor, the sentence names the file and the folder and ends "QUILL is not installed with this copy, so it was not opened." The document stays where the sentence says. There is no install offer and no clipboard.
   - **Inside QUILL**, where Cast's commands run in the editor's own process, nothing is saved. A new, unsaved document opens with the same heading lines and the cursor on the line that was being read, and one sentence names it.
   - **The way back:** the Transcript window stays open with its cursor where it was. The origin line tells you how to hear the line again, and the bookmarks list names the moments.

**Not built, with the reason:** a link in the QUILL document that starts Cast at the moment. That would need Cast to accept a position on its command line or over IPC, which is a new kind of handoff. The pilot decision rules it out until journey A has been observed. The origin line and the bookmarks give the way back in words.

## 4. Acceptance

| Item | Where it is met |
|---|---|
| Distinguish passing a reference, making a copy and creating a transformed output | Section 1. Only the Cast and Radio text handoff makes a copy, and its sentence and file say so |
| Preserve the original and explain where the new artifact lives | The feed and the cached transcript are untouched. The copy's folder and name are in the one sentence. A changed copy is never overwritten |
| Unavailable or gated destinations offer a useful save or export path without an installation detour | Journey A keeps the saved document and names it. Rows 10, 14, 16 and 17 are planned |
| Do not change the receiving app's playback, microphone or account choice unexpectedly | QUILL only opens a document. Cast's playback is not touched, and nothing is paused or ducked |
| Return to the origin restores its selection | The Transcript window keeps its cursor. Bookmarks and session restore return to the moment |
| Exercise portable installs, missing apps, duplicate names, changed files and unavailable remote resources | Tests cover a missing editor, a folder that cannot be written, a duplicate name, an edited copy and sending again. Portable sibling discovery is `build_launch_argv`, unchanged and already tested. A transcript that cannot be fetched already says so before anything is handed over. Live checks are listed in the pull request |

## 5. Pull requests

1. **Journey A** (this document, rows 2 to 6): `feat/m4-journey-a`.
2. **Launches that said nothing or said too much** (rows 7, 14 and 16): `feat/m4-launch-outcomes`.
3. **Release gates on offered destinations** (rows 10 and 17): `feat/m4-release-gates`.
