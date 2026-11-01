# Checks to Try With Your Screen Reader, October 2026

These are the hands-on checks for everything built in late September and early
October 2026 across QUILL Cast, Quill Radio, QUILL Lite and QUILL. There are
316 of them. Each one says where to go, what to press and what you should
hear. Check a box only after you have tried it yourself with a screen reader;
passing automated tests do not count.

Try them with NVDA, JAWS and Narrator where you can. When something is wrong,
write down the check, the screen reader and its version, and exactly what you
heard. Never put document text, passwords or keys in a report.

This list used to live in the working file qc.md, which was retired on
2026-10-03 once all its code work was done. The app-by-app sign-off sheets in
this folder are still the place to start for a release; this page covers what
is new since they were written.

## Release blockers

- **QUILL Transcribe 1.0, releasing 1 November 2026: the screen-reader pass in
  Outlook, Word, Notepad and the browsers is Jeff's, and it blocks the
  release.** Every Notepad, Word, Outlook, Edge, Chrome and Firefox box under
  "QUILL Transcribe Into Other Programs" below must be checked, with NVDA, JAWS
  and Narrator, before the 1.0.0 packages are published. QUILL Transcribe is in
  `RELEASED_APPS` on the branch from 2026-10-16, so a build made now already
  shows it on every QuillVille menu and shows Dictate Here in Quill Cast and
  Quill Radio; that does not make the pass optional. The checks under "QUILL
  Transcribe in the Rest of the Family" are part of the same pass.

## Still to do in the code

- **QUILL's own documentation** -- its user guide, release notes, tutorials and
  the QUILL pages of the website -- gets the same people-first, beginner-first
  rewrite that QUILL Cast, Quill Radio, QUILL Lite and the site received on
  2026-10-03. Jeff asked for QUILL to come last.

This section records user-experience changes implemented in source, not a
release announcement. Test the current source build; older installed builds
may not contain these changes. All manual checks below are pending. Automated
test passes do not mean speech, braille, native Alt+Tab, or every app was
manually verified. Do not check a checkbox until a human completes that check.

Run the keyboard checks separately with NVDA, JAWS, and Narrator. Record the
reader/version, app/build or commit, result, and exact unexpected speech or
focus behavior under the relevant item. Repeat relevant checks with the status
bar hidden and announcement throttling enabled. Never include document content,
tokens, or credentials in the test report.


## Native Preferences Search

Implemented in commit `1822e4c`. Search navigates existing controls; it does not
edit settings, press action buttons, or save the dialog.

Entry points: open the app's existing Preferences or Settings command. In QUILL
and Lite, Preferences is Control+Comma. Radio, Cast, Studio, Weather, and Beacon
use their existing Preferences/Settings menu routes. Native modal and sanctioned
modeless Settings/Preferences surfaces use the same search implementation.

- [ ] On opening, find the named **Find a setting** field by Tab; confirm its
  name and editable role are spoken once and F1 gives useful control help.
- [ ] Type a word from a setting's label or help, such as **recovery** in Lite
  or **auto sync** in Beacon. Focus must stay in the search field as results
  update. Changing the query must not change or save a setting.
- [ ] Press Down to enter **Matching settings**, then arrow through results.
  Confirm each name and selection is read naturally without duplicate app speech.
- [ ] Press Enter on a match. Its actual control receives focus, with its
  current value/state spoken by the reader. Enter in search must not trigger
  the dialog's default OK/Apply or activate an action button.
- [ ] Choose a match on a hidden notebook/book page. Confirm that page is
  revealed before focus moves. In Beacon, a Sync match must show the Sync section.
- [ ] Press Control+F from a setting. It returns to search and selects the
  current query so typing can replace it.
- [ ] Search for a nonexistent setting. Confirm zero matches is reviewable and
  no previous result remains selectable. Count speech is debounced when the
  host supplies an announcement callback; some hosts currently expose only the
  on-screen count. Record silence or duplicate count speech as an acceptance issue.
- [ ] Find a disabled setting where available. Its result identifies it as
  disabled; Enter must not enable it, edit it, or move focus to an unusable control.
- [ ] While search has text, press Escape: it clears the query and keeps the
  window open. Press Escape again with an empty query: the original window's
  cancel/close behavior applies, with no unintended save.
- [ ] Change a setting normally, return to search, then Cancel. Existing cancel
  semantics must remain intact. Repeat with OK/Apply and confirm only intentional
  settings changes are applied. Immediate-action buttons retain their authored
  behavior when deliberately activated outside search.
- [ ] Close while typing a query, then reopen. No delayed result-count speech
  should arrive from the closed window, and the replacement surface must work.
- [ ] Verify Tab/Shift+Tab order, result-list reachability, and readable sizing
  at a smaller window size and increased display scaling.

Coverage: 67 Preferences/dialog/Beacon tests, followed by 29 search/dialog
tests after modeless onboarding and 12 search/Beacon tests after helper
extraction. These include real wx controls, Lite's constructed Preferences,
Beacon's hidden Sync panel, disabled controls, and value/cancel preservation.

Limits: Converter, Player, and Inkwell do not yet have unified Preferences entry
points. Web forms and unopened nested dialogs are not indexed. QUILL's hub
search finds categories and descriptions, not controls in unopened child dialogs.
Do not report this as completed all-app/global settings search.

## Radio and Cast Transport State

The primary transport action must say what pressing it will do, **and to
what, in its visible label** (implemented 2026-10-01, X-06). Radio's
main-window contract is a single button: stopped offers "Play <selected
favorite>" (Alt+L), active offers "Stop <what is playing>" (Alt+T), and paused
offers "Resume <it>" (Alt+U); with a folder or nothing selected it reads "Play
-- nothing selected" and pressing it says what would work. Cast has a primary
"Play <selection>" / "Pause <episode>" / "Resume <episode>" button (Alt+Y,
Alt+S) plus a separate Stop (Alt+T) that is disabled when nothing is playing
or paused. The object is in the label because an accessible name on a wxMSW
button is never read. The label, enablement, and action must agree. Do not
announce a state the focused native control says. The Volume slider in Radio's
main window is now Alt+O.

Entry points: Radio's main player window and Cast's main podcast window. Test a
playable station/show, a local or recorded item, and a bounded Cast episode.

- [ ] With playback stopped and a playable target selected, Tab to the primary
  transport. It must be enabled and read "Play" followed by the name of the
  selected station/show/episode -- the name you gave a renamed favorite, in
  Radio. In Cast, separate Stop must be disabled, never an enabled dead action.
- [ ] Arrow the list to a folder (Radio), a folder, an empty show or a view
  with nothing playable (Cast). The button must read "Play -- nothing
  selected"; pressing it must say which two things would work and start
  nothing. Arrow back to a playable row: the label must follow without
  anything else being said.
- [ ] Select a podcast whose title is longer than forty characters. The label
  must end with an ellipsis and the button must not change width; Tab onward
  and confirm the buttons after it did not move. A title containing an
  ampersand must read naturally and not create a stray Alt key.
- [ ] In Cast, select a podcast: the Unfollow button must read "Unfollow" and
  that podcast's name. Select one of its episodes: the same. Select a folder:
  plain "Unfollow", disabled.
- [ ] Start playback. Radio's primary button changes to Stop; Cast's changes to
  Pause, with separate Stop available only when it can stop active playback.
- [ ] Pause a bounded Cast episode. Resume and the episode's name must be
  offered (Alt+S, the same letter Pause had) and continue at the saved
  position; no control may be mislabeled as Stop. In Radio, pause a podcast or
  recording with Ctrl+Space: the main window's button must read "Resume" and
  its name, Alt+U must press it, and Playback > Play must read Resume too.
- [ ] Stop playback. Radio returns to Play. Cast returns its primary button to
  Play and makes separate Stop unavailable. Do not duplicate Play in that row.
- [ ] Repeat with no selection, a folder/view, live Radio, loading, natural
  completion, and failure. No enabled action may promise an impossible result.
- [ ] Invoke actions by keyboard. Labels, spoken names, menus, and hotkeys must
  agree; refreshing the state must not steal focus. Record exact speech/state.

Coverage: `tests/unit/core/test_transport_button.py` (every label and sentence
the shared module can produce), `tests/unit/ui/podcasts/test_cast_transport_row.py`
and `tests/unit/ui/radio/test_main_transport_button.py` (both rows on fake
hosts, every state), `tests/unit/ui/test_button_mnemonics.py` (the real Radio
frame against its real menu bar), and GATE-15 with run-time labels. This
cross-app physical reader and main-window enablement matrix remains unrun;
record exact speech after running it. Two conscious gaps to listen for: Radio's
status-bar Play cell and the player panel's Play/Stop button still say the
bare verb.

## Cast Find in Library

- [ ] In Cast's main window press Ctrl+F: focus is in "Find in library". Type
  part of a podcast name: nothing is spoken per letter; when you stop, the count
  is spoken once.
- [ ] Down Arrow: the first match is read with what it is ("-- a podcast",
  "-- an episode of ..."). Enter plays it; the Play button names it; Shift+F10
  opens the usual menu.
- [ ] Escape from the box: "Back to your library", and the cursor is on the row
  it was on before searching.
- [ ] View menu: Find in Library shows Ctrl+F; Customize Features shows
  Ctrl+Alt+C and opens with that key.

## Cast Episode Filter Tests

- [ ] Open a podcast's Episode Filters, Add Rule. Alt+S reaches "More tests";
  Alt+A opens "Episode Filter Test" with focus on "Look at". Choose Show
  notes, Test "contains", Value "sponsor", Save: the list reads "Show notes
  contains "sponsor"" and "Test added" is spoken.
- [ ] In Episode Filter Test choose Look at: Episode type. The Test list
  becomes whole phrases ("is a trailer") and Value is dimmed. Choose Length
  in minutes, type "ten" and Save: refused with the reason, focus on Value.
- [ ] Set Match when (Alt+W) to "Any one test is enough" with two tests, then
  Try It on Recent Episodes (Alt+Y): the count and up to five titles are
  spoken once; Alt+U reads the same sentence. The rules list row starts
  "Any one of:".
- [ ] On an episode you do not want, Shift+F10, F: Episode Filters opens and
  the rule window appears on its own; its first line says why the rule was
  chosen and how many of the newest it catches. Save the rule: "Rule added
  and filtering switched on". Cancel Episode Filters: nothing was stored.

## Cast Phase 1 Small Fixes

Each row is one small Phase 1 fix, checked by ear in QUILL Cast's main window
or the named dialog. Record exact speech.

- [ ] Press Ctrl+, in Cast. In the Podcasts group, "Where to land on launch"
  (Alt+U) reads "What is new..."; choose Favorites, OK, close and reopen Cast:
  focus lands on Favorites even when it is empty. Set it back to What is new.
- [ ] Open an episode's Show Notes, choose View as: Rich text, then Tab. The
  formatted notes are announced as "Show notes, formatted"; Alt+F reaches
  them; choosing Plain text hides the label with them.
- [ ] Press F1 in the main window (focus on the library) and in Feed Check.
  The first paragraph describes the window as it is now: the main window's
  buttons name their object, places are in the View menu, F6 reaches the
  status bar; Feed Check is worst first and opening it checks nothing.
- [ ] With the network off, Preview a search result in Add Podcast: the
  failure is spoken once, and Preview is usable again. Import an OPML file
  with feed checking on while offline: either per-feed results, or "The
  feed check could not run. Everything you imported is kept" -- never
  "checked 0 feeds".
- [ ] Shift+F10 on a podcast in the library: the menu says Unfollow...
  (Delete). Preview a search result in Add Podcast: the button says Follow.
  Podcasts menu: Follow ACB Media Podcasts. Unfollow a podcast, press
  Ctrl+Z: "Undid Unfollow" and what came back. No surface says Subscribe
  except where it names the OPML subscription-list file.
- [ ] Open Settings for This Podcast on a podcast with its own speed. Beside
  the speed field, the button reads "Use shared default for" and the
  setting's name; pressing it drops only that answer. Use Shared Defaults
  (Alt+D) asks first and says how many it dropped.
- [ ] In the main window's library tree, press Shift+F10 on a podcast, a
  folder, a pinned view and an episode, then the Applications key on each.
  Each opens the same menu a right-click does, once (not twice).
- [ ] Open Downloads, Podcasts > Feed Check..., an episode's Show Notes,
  Listening Statistics, and Year in Review from Statistics. Each opens with
  focus on its list, notes or report -- the first thing read after the
  title is content, not a filter or a button.
- [ ] Press Ctrl+Shift+Q (or View > Play Queue...): the Play Queue opens with
  focus in the queue list and its title read once. In QUILL, open the Sticky
  Notes Browser: it opens with focus in the search field.
- [ ] In Simple mode (View > Advanced Features unchecked), open Help: Keyboard
  Shortcuts... (Ctrl+Alt+Shift+W) and Global Hotkeys... (Ctrl+Alt+Shift+H)
  are present and open their windows; the Advanced Features announcement
  now counts two fewer rows.
- [ ] Smart Playlist Rules, Podcast Settings, Settings for This Podcast: the
  OK button is announced as "OK" with no shortcut; Alt+O does nothing; Enter
  saves and closes.

## Cast Watched Folders and the 2.0 Follow-Ups

Checked by ear in QUILL Cast with a scratch folder you can drop files into.
Record exact speech.

- [ ] Press Ctrl+Alt+W. "Watched Folders" opens on "No folders yet. Press Add
  Folder to choose one." Press Alt+A, choose the scratch folder, and Save the
  settings page as it opens. Cast says it is watching the folder.
- [ ] Copy a 40-second MP3 into the folder. Within about ten seconds Cast says
  "New in <folder>: <title>, 1 minute." Ctrl+Shift+U shows it in Personal
  Audio. The original is still in the folder.
- [ ] Copy the same file in again under another name: nothing is said and no
  second episode appears. Copy a two-second file: nothing arrives.
- [ ] Start copying a large file over a slow link (or a network share): nothing
  is said until the copy finishes; then it arrives once.
- [ ] Folder Settings (Alt+S): set Tell me to "Say how many arrived", copy two
  files: "2 new recordings in <folder>." Set it to Quietly: nothing is said,
  and Notifications (Ctrl+Shift+N) has the arrival.
- [ ] Pause (Alt+U), copy a file: nothing arrives. Resume: it arrives.
- [ ] Rename the folder in File Explorer: Cast says once that it is
  unavailable, "Still watching." Help > Recent Problems lists it. Rename it
  back and press Scan Now: it recovers silently.
- [ ] Remove (Alt+M): the question starts on No; Yes says its files stay in
  Personal Audio, and they do.
- [ ] Ctrl+Alt+Shift+F12 from another program shows and hides Cast. Ctrl+Alt+Shift+Down
  in Cast marks the playing episode played and moves to the next.
- [ ] Episode menu: Player Information... (Ctrl+I) opens the report; Bookmark
  This Moment (Ctrl+Alt+A) saves a bookmark; Skip Silence (Ctrl+Shift+9)
  says it is on, then off. Podcasts menu: Carry My Place Between Machines...
  (H) opens its window.

## Cast Listening Extensions (Phase 7)

Checked by ear in QUILL Cast while an episode plays. Record exact speech.

- [ ] Ctrl+Shift+T: "<position> of <length>, <n> minutes left." At 1.5x it
  adds the real time; with a sleep timer it adds when it stops.
- [ ] Ctrl+Home from the Places list, an episode list and the status bar lands
  on the launch place's first row. In the show notes it moves to the top of
  the text instead.
- [ ] Shift+Space on an episode: "<title> plays next, after this one." It plays
  when the current episode ends. In Find, Shift+Space types a space.
- [ ] Ten seconds before an episode ends with more queued: "Next: <title> from
  <podcast>." Not during Quiet Hours; not with Stop After This Episode on;
  never twice for one episode.
- [ ] Copy a feed address, press Ctrl+N: Add Podcast opens with it filled in,
  the cursor on it, and it says so. Enter follows.
- [ ] Ctrl+Shift+D, type a note, Enter: "Bookmarked <time> in <episode>."
  Ctrl+Shift+J lists only this episode's bookmarks; Now Playing's Bookmarks
  (Alt+O) does the same; About This Episode has a Bookmarks tab whose Go There
  plays from that moment.
- [ ] Space on an episode plays a short sound and speaks. Preferences > Telling
  you > When a one-key action works: Play a sound -- only the sound; Neither --
  silence, the status bar still shows the words.
- [ ] Help > Global Hotkeys lists only Cast's commands, including Podcasts: Now
  Playing window and Podcasts: Time Remaining; a key given to each works from
  another program.
- [ ] Unfollow two podcasts. Edit > Undo History lists both, newest first;
  Undo This One on the older one brings back only that one. The same in Quill
  Radio.

## Cast Nothing Silent (Phase 3) -- the per-window listen

Open each surface, press each button, and write down exactly what was heard.
A button that changes something and says nothing is a bug to file.

- [ ] Add Podcast: Find with an empty field ("Type a podcast name to find."),
  Find ("Searching...", then the count), Find with the network off ("Find
  failed: ..."), Add with an empty address ("Type a feed URL first."), Add a
  bad address ("Fetching ...", then "Could not follow it: ...").
- [ ] Preview a result: "Loading <title>..."; with the network off, the
  failure is said once and appears in Help > Recent Problems.
- [ ] Search Everywhere: a search says its count; clearing says "Search
  cleared."
- [ ] Import OPML with feed checking on: the percentage is said every few per
  cent; the end says how many were checked and how many were unreachable.
- [ ] About This Episode on an episode with chapters to analyse, transcripts,
  Follow on a recommended podcast with the network off: each failure is said
  and listed in Recent Problems.
- [ ] Unplug the drive of a watched folder: said once, listed in Recent
  Problems, not repeated on the next look.
- [ ] Every other Cast window: press every button once; record any that is
  silent.

## Cast Earshot Parity R8-R10

- [ ] Rename an episode with F2, press F5: the name stays. Rename it to nothing:
  "Back to the feed's own name, ...". The same for a podcast.
- [ ] In the Notifications place and the Notifications window, on a
  new-episode notice: Ctrl+Enter plays it; Space says "Added ... to the Play
  Queue." with the added sound.
- [ ] Podcasts > Clear All Podcast Data from This Computer (Advanced): both
  questions say this computer only, and start on No; cancelling says "Nothing
  was cleared."

## Cast AI Verbs and Tidy the Podcasts I Follow

AI help on and the agreement accepted, unless a row says otherwise.

- [ ] Organise My Podcasts: the review list reads "Accept: Move: ..." rows; Space
  says Skip/Accept; Apply Selected says how many folders and moves; Escape
  says "Nothing was changed."
- [ ] What Is This Podcast About and Summarise This Episode: the answer is
  spoken, then shown read-only with Copy; the summary starts "From the
  transcript" or "From the show notes".
- [ ] Is This Episode for Me with no note set: asks for the note first. With a
  note: one sentence starting Yes, Probably, Probably not or No.
- [ ] Build Me a Listening Run, 30 minutes: the run's total is said, the
  list fits, Apply adds them to the queue in order.
- [ ] Smart Playlist from a Sentence: the rules are read as sentences; Apply
  saves a smart playlist that shows the right episodes.
- [ ] Name These Chapters on an analysed episode: per-chapter Accept/Skip;
  without analysis it says to run Analyse Chapters first.
- [ ] With AI help off: Tidy the Podcasts I Follow still works and sends nothing;
  every other row says AI help is switched off.

## F-10 Adoptions: Progress, Results, and the Cursor

- [ ] Cast, 8 or more podcasts: F5 says "Checking feeds, 25 percent" and so on,
  then one sentence; F9 repeats it; Shift+F9 lists it; with a broken feed, the
  row offers Retry.
- [ ] Cast: Download All Episodes on a podcast with 4 or more missing: quarters,
  then "Downloaded 4 of 4 episodes of ..."; Activity's Open Folder opens the
  download folder.
- [ ] Cast: Export OPML, Export My Data, Year in Review Save: each appears in
  Activity with Open Folder. Following a podcast appears too.
- [ ] Cast: Delete on the third row of the Inbox: the cursor is on the row that
  moved up, not the first.
- [ ] Radio: a recording that finishes is in Activity, "Recording saved: <station>,
  started <day time>, <length>, in <folder>.", with the file name and Open
  Folder; one that captured nothing is listed as failed with its reason.
- [ ] Radio: record a station, then disconnect the network until the reconnect
  attempts run out. One message, on the error sound: "<station> recording ended
  early. Saved N of M minutes, in <folder>. Reason: ...". No "Recording saved"
  was heard at any reconnect. Activity lists it as partial. On a 40-cell braille
  display the saved amount is on the first line.
- [ ] Radio: while a dropped recording is waiting to reconnect, Ctrl+Alt+X says
  "Stopping all 1 recording, including 1 waiting to reconnect..." and the
  recording does not start again.
- [ ] Radio: with Format set to Raw stream, the finished recording appears in
  Radio Recordings (Ctrl+Shift+R).
- [ ] QUILL Lite: open a large file from a network drive; Shift+F9 while it
  opens, and again after: Opened <name>.

## Cast First Run and Tutorials (Phase 6)

- [ ] On a fresh profile with no podcasts: one welcome window. Tab reaches
  "Where would you like to land each time?"; choose Favorites, Done; reopen
  Cast: it lands on Favorites. Skip (Escape) changes nothing and never returns.
- [ ] Add Your First Podcast (Alt+A) closes the welcome and opens Add Podcast.
- [ ] Help > Tutorials (Ctrl+Alt+F1): five tracks; The first hour, Places,
  Find, Now Playing and When something breaks are in the first. Try It on a
  step with a command does what the step says.

## EPUB Maths (X-08)

- [ ] Open an EPUB whose MathML has a less-than sign (x &lt; 3): the equation
  reads "x less than 3", not "x 3".

## Settings Search Reach, Recipes and Working Modes (X-01 to X-04)

- [ ] Cast Preferences on When Cast opens: type "original" in Find a setting;
  the Data section's watched-folder row is listed; Enter shows Data and puts
  focus on it.
- [ ] Converter, Media Player and Inkwell: Ctrl+Alt+Shift+S opens Find a
  Setting or Command; typing narrows; an option row says on or off; Enter
  switches it and says the new state.
- [ ] QUILL without a screen reader: Preferences > GLOW Accessibility shows a
  Find a setting box; Enter moves to the first match.
- [ ] QUILL: Preferences > Task Recipes and Working Modes. Quiet background
  work previews its changes; Apply says how many changed; Put Back restores
  them. Turn Focus on for this session only, restart QUILL: Focus is off and
  every setting is back.
- [ ] Shift+F9 during a Download All batch in Cast: the summary says "Still
  working: Downloading ...".
- [ ] Cast's Play Queue: an episode Auto-Queue added reads "...; queued by
  Auto-Queue"; one you added with Space says nothing extra.

## Shared Choices Between Apps (X-05)

- [ ] In Cast, turn on Announce dialog transitions and Share these choices
  with my other Quill apps; save. In Radio, turn on Share these choices; on
  save Radio says it is now using your shared choice for announce dialog
  transitions, and it is on.
- [ ] Turn sharing off in Radio, change the choice in Cast: Radio is
  unchanged at its next launch.

## Windows That Stay Open (Cast Phase 4)

- [ ] Ctrl+Alt+Shift+S, Escape: focus is back where you were; Ctrl+Alt+Shift+S
  again brings the same Statistics window, refreshed, and it is in the Window
  menu.
- [ ] Settings for This Podcast: change a value, Ctrl+S; the window stays open
  and says it saved; Escape returns to the podcast row.
- [ ] Episode Filters from Filter Episodes Like This: Save keeps it open; Close
  after an unsaved edit leaves the stored rules unchanged.
- [ ] New Smart Playlist: first Save makes it; a second Save updates the same
  playlist (no duplicate in Playlists).
- [ ] Add Podcast: follow a result, go to the library with Alt+Tab or the
  Window menu, come back; the results are still there.
- [ ] Read Transcript on one episode, then on another: one window, showing the
  second; Radio's transcript is still a dialog.
- [ ] Podcast Sound Enhancements: Apply changes the sound and the window stays
  open; Close leaves it as applied.
- [ ] QUILL's Podcast Manager (modal): open Episode Filters and Show Notes
  from a row; both are usable and close with the Manager.
- [ ] New Folder from the tree, the picker and Move to Folder: the same
  "Folder name:" box each time.

## Earshot B1-B3

- [ ] Listen to an episode in Earshot with Listening Places on; Sync Now in
  Cast; Continue Listening's row ends "last played on Earshot". Play it in
  Cast; the phrase goes.
- [ ] Two Cast machines, both with Also share the podcasts I follow on: follow
  a podcast in a folder on one, Sync Now on both; it appears on the other in
  that folder, and the sync sentence names it.
- [ ] Unfollow it on one, sync both: it goes from the other, named; its
  downloaded episodes are still on disk.
- [ ] A private feed (with a sign-in) is not in the shared file; the sync
  sentence says one private feed stayed on this device.

## Library and Inbox Views

- [ ] Ctrl+Shift+R: change Show the library as to Folders only; Escape; the
  Podcasts place lists only folders, closed, and "Podcasts in no folder" last;
  Right Arrow opens one.
- [ ] Podcasts only and Together by name read as described; no podcast is
  missing in any layout.
- [ ] Counts say: No counts; rows read names only.
- [ ] Show the Inbox as Folders first: folder rows lead ("News, folder, 5 in the
  Inbox"); Enter shows that folder's episodes; Backspace returns to the row.
- [ ] Preferences > The library holds the same choices; changing one there
  redraws the library after Save.

## Documentation Voice (Cast, Radio, Lite, the site)

- [ ] Read one chapter of each guide aloud with the screen reader: no sentence
  sounds machine-written; the closing "What you learned, and where to go next"
  names a real next chapter and a real lesson.
- [ ] Heading navigation (H, then 2/3/4) in each guide's HTML walks a true
  outline: subtopics sit one level under their topic, nothing skips a level.
- [ ] Help > Tutorials in Cast, Radio and Lite: the lessons read warmly and say
  what you will hear.
- [ ] quillforall.org home, Radio, QUILL Lite, FAQ and compare pages read as
  beginner-first, with one H1 each.

## Radio and Cast Closing Report

Entry: Quill Radio and QUILL Cast. To force a failure, make the data folder
read-only (or fill the disk) just before closing, then restore it.

- [ ] Close Cast with the folder read-only. It closes as usual. Restore the
  folder and start Cast: one sentence says it could not finish saving and
  names what; it is not repeated on the next launch.
- [ ] Help > Recent Problems: a "Closing" row is there; Retry says the
  library and statistics were saved now.
- [ ] Repeat in Radio: the sentence names noting when it closed or the
  recording note; Retry while recording keeps the recording note and says so.
- [ ] A normal close of either app says nothing at the next launch.

## Lite Background Open

Entry: a plain text file of several megabytes on a local disk, and any small
file on a network share.

- [ ] File > Open the large file. A new window's title says its number and
  "Opening"; "Opening" and the name is spoken once; typing does nothing until
  the text arrives; then focus is at the top of the text and the title is the
  file's.
- [ ] Open it again while it is still opening: focus moves to that window; no
  second window opens.
- [ ] Open the large file and press Ctrl+W at once: the window closes, nothing
  is announced later, and nothing appears in another window.
- [ ] Open the network file, then disconnect the share before it arrives (or
  use a path that cannot be read): the box names the reason and asks Try
  again?; No closes the empty window, Yes reads again.

## Lite Multi-Instance Settings

Entry: start QUILL Lite, then start a second with `--new-instance`.

- [ ] In the first, turn Word Wrap off (Alt+Z). In the second, change the
  theme in Preferences. Close the first, then the second. Start QUILL Lite:
  Word Wrap is off and the theme is the one the second chose.
- [ ] With both open, change a setting in one: the other does not change or
  announce anything until it is restarted.

## Lite Settings-Save Failure and Retry

Implemented in commit `6eaab53`. Accepted choices stay active for the current
session when writing settings fails. This is separate from document saving.

Entry points: Tools > Preferences (Control+Comma), plus ordinary settings
changes such as word wrap or appearance. Use a disposable development/test
profile and a controlled write failure; do not make the real user profile
read-only or fill the machine's disk to test this.

- [ ] Accept a setting while its store cannot be written. Expect:
  **Settings could not be saved. They remain active for this session. Reopen
  Preferences to retry.** Confirm Preferences does not then falsely say
  **Preferences saved**.
- [ ] Confirm the chosen setting works in the current session despite the
  persistence failure. The editor remains usable and the document is unchanged.
- [ ] Use F6 to review the status bar's Message cell. The failure remains
  reviewable after another action, document editing, and ordinary message expiry.
- [ ] Repeat a failed change. Check warning coalescing and configured speech
  throttling; record any missing failure outcome or excessive repeated warning.
- [ ] Restore write access and reopen Preferences. It retries already accepted
  settings without another edit or OK. On success, expect **Settings are now
  saved**, and the persistent warning clears.
- [ ] Make a new edit inside that reopened Preferences window and Cancel.
  Cancel discards that new edit; it does not undo the successful retry of choices
  accepted earlier. Reopen/relaunch to confirm only accepted values persist.
- [ ] With a settings warning queued, exit. It must be reported before teardown
  rather than delivered into a destroyed window. No exception dialog should appear.
- [ ] Repeat the failure with the status bar hidden. Record whether the spoken
  warning is sufficient and whether a review route is discoverable.

Coverage: 50 settings/status/Preferences/lifecycle tests, including real
filesystem failure followed by a successful atomic write, stale-warning
suppression after retry, preserved session values, and a pending warning at exit.

Limits: direct Retry/Open Settings Folder activity actions and adoption by other
settings/history writers remain open. Fault injection and diagnostics must not
expose raw filesystem errors, user paths, or sensitive contents.

## Lite Activation and Alt+Tab Focus

Implemented in commit `53406c3`. Activation makes one event-loop focus check
and one bounded settling check. Old checks are invalidated when activation
changes. Only container/missing focus is repaired; intentional control focus
must be left alone. The app does not announce the focus move itself.

Entry point: open a Lite document and switch to another application with Alt+Tab.

- [ ] Alt+Tab back repeatedly, then type immediately. Text must enter the
  active document, not disappear into the shell or MDI client. Confirm ordinary
  reader focus speech is not duplicated by an app announcement.
- [ ] Leave and return while a Find field or another interactive control has
  focus. That control must keep focus and remain usable; typing must not be
  redirected to the document unexpectedly.
- [ ] Repeat around open menus. Navigation must remain in the menu rather
  than being interrupted by the delayed focus repair.
- [ ] Rapidly leave again before the settling check. The app must not steal
  focus back from the newly active application.
- [ ] Repeat with several documents, after switching with Control+Tab or
  Control+F6, after opening a child, and after closing the active child. Focus
  must refer to the currently active document, never a destroyed or old child.
- [ ] Minimize/hide the shell and close it while activation work is queued.
  No background focus grab, stale speech, or exception dialog should occur.

Coverage: 21 focus tests, including real wx MDI/text controls over five
repair/preserve cycles; the preceding activation/lifecycle suite passed 28 tests.
Physical Alt+Tab and actual reader output remain human acceptance, not automated
passes. A reusable family helper and unsuccessful-repair diagnostics remain open.

## Lite Inbox and Exit Lifecycle

Implemented in commit `fb9f32d`. Confirmed Exit/shell close stops app-owned
polling before child destruction; final cleanup is idempotent. Cancelled close
keeps the app active. Pending external open requests are retained for a later
launch, and a deferred launch-update check does not start after shutdown.

Entry points: normal Exit, Alt+F4 on the shell, and opening a file through a
second Lite launch while the first instance is running.

- [ ] Exit with several documents. Save/discard prompts must remain operable,
  and exit must not cause a late document window or exception dialog to appear.
- [ ] Cancel a save/discard prompt during exit. The existing app must remain
  usable and accept a subsequent file-open request from a second launch.
- [ ] Send a request around confirmed exit. Confirm no document opens in the
  dying shell; retained requests must be handled on the next appropriate launch.
  The queued-tick timing itself is covered by automated tests.
- [ ] Exit soon after launch. No deferred launch-update dialog should appear
  after shutdown begins. Repeated/final cleanup must not produce duplicate cues.
- [ ] Check focus and speech around prompts, veto, and successful close. Only
  intended action outcomes and existing native focus/title speech should occur.

Coverage: 23 construction/lifecycle/update tests, including forced close,
veto, repeated finalization, pending requests, and delayed checks.

## Shared Background Callback Lifetime

Implemented in commit `84de01d`. Task-manager shutdown suppresses queued and
late success, failure, and progress delivery. Work/results may continue to
exist; UI delivery suppression is not the same as cancellation.

- [ ] When testing an adopted app task, close its owner while it is pending.
  No later speech, focus move, status update, or exception may target the closed
  surface. Record the specific task and app, not merely a generic pass.
- [ ] Reopen a replacement surface and start another task. It must receive
  its own result, never the old surface's callback.
- [ ] Confirm that cancellation feedback and completed results follow the
  feature's documented policy; suppressing stale UI callbacks must not silently
  erase work that the feature promises to retain.

Coverage: 12 focused task-manager tests for queued success/failure/progress,
repeated invalidation, replacement tokens, shutdown, and retained futures.

Limits: per-surface token adoption, persistent Activity/Problems history, direct
timers, and arbitrary CallAfter callbacks are not completed by this manager fix.
Add each actual adoption here as it lands before asking for feature-level SR testing.

## Core Registry Ownership

Completed QC2 F-07 in commit `1822e4c`. This is an internal thread contract,
not a new reader interaction. No dedicated speech script is required.

- [ ] During normal app regression, confirm keyboard commands, command palettes,
  and extension commands still work, without new error dialogs or unexpected speech.

Coverage: 77 registry/Quillin tests and strict mypy. Worker access is rejected
before state changes or handler dispatch. Readers do not need to provoke that
programming-error path manually.

## Cast Earshot Parity R3 and R4

- [ ] Shift+F10 on an episode, Refresh Episode Audio...: Cast says it is
  checking the feed, then asks once, naming the download; Yes downloads it
  again and says so; your place in the episode is unchanged.
- [ ] Preferences > Data, turn on Delete its downloaded file; in the Inbox,
  Delete on a downloaded episode says "Its download was deleted." and the file
  is gone; an episode marked Keep This Episode keeps its file.

## Quill Radio YouTube, Live Against Real YouTube (before 3.2.0 ships)

Every YouTube feature so far is tested only with stand-ins. Try these on real
YouTube with JAWS and with NVDA. Note anything that is silent, chatty, or moves
your place when it should not.

- [ ] Station > Search YouTube... (Ctrl+Shift+6): search for a channel you know.
  The count is said once; rows read title first, then the kind (video,
  playlist, channel). Enter on a video plays it; Enter on a channel opens
  Uploads, Shorts, Live and Playlists.
- [ ] Video > YouTube > Search YouTube with Filters... (Ctrl+Alt+Shift+0): try
  "This week", "Over 20 minutes" and sort by views; then a YouTube Music song
  search. Results land under Search Results.
- [ ] Video > Read Comments... (Ctrl+Shift+7) on a popular video: rows read
  author first; replies say who they answer; emoji are read as words; a link
  reads as "link to ...". Search filters as you type and the count is said
  once. Load More adds rows and your place does not move. Escape returns you
  where you were.
- [ ] Video > YouTube > Live Chat... (Ctrl+Alt+Shift+7) on a busy live stream:
  - Arrow through the list while messages arrive: nothing moves you and nothing
    re-reads.
  - Space pauses; on resume the waiting count is said once.
  - Ctrl+Up and Ctrl+Down jump between one person's messages; Ctrl+J goes to
    the newest; Ctrl+L reads the newest without moving; Ctrl+T says when the
    selected message was sent.
  - Turn on Speak new messages: a burst is summarised ("12 new messages"),
    nothing is spoken more than once every 4 seconds, and Ctrl+S turns it off.
  - Try "only messages mentioning a word" with a word likely to appear.
  - F6 and Shift+F6 move between the list, Full text and the filter.
- [ ] Live Chat replay on a finished stream that had chat: messages appear in
  step with playback.
- [ ] Video > YouTube > YouTube Video... (Ctrl+Alt+Shift+8): the status line
  (live, finished, or "Starts in ..."), the description, and Moments in the
  description: Enter jumps when that video is playing. On a premiere, Remind
  Me When It Goes Live sets a reminder. Save Audio queues a download.
- [ ] Preferences, YouTube group: turn on Use my YouTube sign-in from my web
  browser with your usual browser. My YouTube appears under YouTube with Home,
  Subscriptions, Watch Later, Liked Videos, Your Playlists and History. If the
  browser refuses, Quill Radio says so once in plain words.
- [ ] A members-only or age-restricted video your account can watch plays with
  the browser sign-in on, and is refused politely with it off.
- [ ] Video > YouTube > Skip Sponsor Segments... (Ctrl+Alt+Shift+9): turn it on
  and play a video known to have a sponsor segment. "Skipped a sponsor
  segment." is said once per skip.
- [ ] On a followed channel, Notify Me About New Videos: after its next upload
  and the next podcast refresh, one "New on <channel>" notice; Enter on it in
  Notifications plays the video.
- [ ] Hidden until Google approves: none of these appear anywhere in a public
  build: Connect YouTube Account, Reply / Add a Comment / Delete My Comment, a
  Send box in Live Chat, Like / Dislike / Add to Playlist in the YouTube Video
  window.

## Built 2026-10-04, Not Yet Tried Live

Everything here passed its automated tests on 2026-10-04 and has not been tried
by hand. Use an installed build for the Quill Radio checks, because Open with,
Default apps and the right-click verbs come from the installer.

### Quill Radio as a media player

- [ ] In File Explorer, select an MP3 and press Shift+F10, then choose Open with.
  Quill Radio is in the list, with its own name and icon. Choosing it plays the
  file and what is playing is said once.
- [ ] Settings > Apps > Default apps lists Quill Radio. Nothing changed which
  app opens any type until you chose it there.
- [ ] Preferences > Windows and your files > Make Quill Radio My Media
  Player... (Alt+Q) on a portable copy: Windows' Default apps page opens on
  Quill Radio, and the button's result is said in one sentence.
- [ ] With Quill Radio already running and minimised, open a file from
  Explorer. It plays in the running copy, the window does not jump in front,
  and no second copy starts.
- [ ] Select five files in Explorer and press Enter. They become one Opened
  files list in Local Media, playing from the first; Next and Previous move
  through them. Opening another file afterwards replaces the list, unless you
  kept it with Save as Playlist... (Ctrl+S in Local Media).
- [ ] A file in a folder with a space in its name (for example C:\My Music)
  plays, rather than being said as missing.
- [ ] Right-click verbs, on an MP3 and on an M3U: Play with Quill Radio plays
  it; Add to Quill Radio Playlist adds it to the end of the Opened files list
  without interrupting what is playing, and says how many were added.
- [ ] A missing or unplayable file is one plain sentence, not a dialog.
- [ ] Uninstall Quill Radio, then check Open with and the right-click menu:
  neither mentions Quill Radio any more, and other players are untouched.

### Opening files in QUILL and QUILL Lite

- [ ] Drag and drop, in both editors: drag one file, then three, from File
  Explorer onto the window. Each opens in its own document and one sentence
  says how many opened. Dropping selected text on the editor still inserts it.
- [ ] Open from Clipboard (Ctrl+Alt+Shift+Enter), in both editors: with files
  copied in Explorer (Ctrl+C), each opens. With a file path copied as text, it
  opens. With a web link copied, Open from URL asks first, naming the website
  and the size. With nothing usable copied, one plain sentence says so.
- [ ] QUILL's File menu: Alt+F, P opens Print. Alt+F, X still exits and Alt+F, E
  still opens Export.
- [ ] QUILL, File > Open Recent: Alt+Shift+1 reopens the most recent document,
  Alt+Shift+2 the one before, through Alt+Shift+8 (Alt+Shift+9 is AutoCorrect
  Entries); Alt+Shift+0 opens Recent
  Documents. Each row of Open Recent says the file's name first, then its
  folder, and says how to reach it from the keyboard.

### QUILL Lite's outside-change watcher

- [ ] Open a .md file in QUILL Lite, then change and save it in Notepad. Within a
  second or two QUILL Lite asks once: Keep Mine, Reload from Disk or Save As...,
  with Keep Mine on Enter. Keep Mine leaves your text and your place alone.
- [ ] With Preferences > When another program changes the file > Reload
  automatically when you have no unsaved edits turned on, an untouched document
  reloads quietly, your cursor stays on the same line, and you hear it once.
- [ ] Check Do not ask me again for .md files with Reload. Change the file
  again: it reloads without asking. Now type something (unsaved) and change the
  file once more: QUILL Lite asks rather than reloading over your edits. Try the
  same in QUILL.
- [ ] Change a file that belongs to a document in the background: nothing is
  said until you switch to that document, then the question comes once.
- [ ] Delete the file in Explorer: QUILL Lite says so once, keeps your text, and
  Save As is offered next time you save.

### The launcher, from a folder with a space

- [ ] Unpack a portable Quill Radio, QUILL Lite and QUILL Cast to a folder such
  as C:\Portable Apps\Quill Radio and start each from there. Each starts; none
  shows the "did not start" window.
- [ ] From that folder, open a file whose own path has a space through Open
  with. It opens as one file.

### Quill Radio backup: What Was Left Out

- [ ] Back up Quill Radio with one recording kept only in OneDrive (not on this
  computer) and one file open in another program. The result offers Show what
  was left out, and why?. Yes opens What Was Left Out: one row per item, the
  reason read with each, what to do under the list, and Copy List beside it.
  Escape closes it and returns you to where you were.
- [ ] The same list is in Recent Problems afterwards.
- [ ] A backup with nothing left out says nothing about skipped items at all.

## Dictation, Built 2026-10-05, Not Yet Tried Live

Everything here passed its automated tests on 2026-10-05 and has not been tried
by hand. Try each one in both QUILL (Tools > Speech > Live Dictation) and QUILL
Lite (Tools > Dictation), with NVDA and with JAWS, at the screen reader's
default punctuation level and again at its lowest. Use headphones so the
microphone does not hear the read-back.

### The read-back says the punctuation

- [ ] Dictate "hello comma world period". The read-back says "Hello comma world
  period" with the marks spoken as words, at every punctuation level, and your
  screen reader does not also read the same line a second time. The status bar
  and a braille display show "Dictated: Hello, world."
- [ ] Dictate a quotation and a question. You hear "open quote", "close quote"
  and "question mark" in the read-back; "new paragraph" is said as words too.
- [ ] Dictate "it's 3.5 percent of 1,000" and "example dot com": the apostrophe
  and the marks inside the numbers are silent, and the address is read as
  "example dot com".
- [ ] Uncheck Say punctuation marks in the read-back in More Dictation Settings
  (Alt+S there). The read-back now says only the words.

### Selecting and moving by voice

- [ ] With a few lines of text, say "select" and two words that are above the
  cursor. You hear "Selected:" and the words once, not twice, and your screen
  reader's own selection announcement does not talk over it. Say new words: they
  replace the selection.
- [ ] Say "go to" and words near the cursor: you hear "Before" and the words.
  Say "go after" and words: you hear "After" and the words. For words three or
  more lines away, the line number is added, such as ", line 40".
- [ ] Say "select" and words that are not in the document. You hear "Not found,
  written as text." and the phrase is in the document; "scratch that" removes
  it.
- [ ] Say "correct" and words: you hear "Correcting" and the words, then "Say
  the new words".

### Capitals, spelling and language

- [ ] Say "caps on". You hear "Caps on." and the status bar shows it. Dictate a
  sentence: every word starts with a capital. "Caps off" ends it.
- [ ] Say "no space on", dictate "example dot com", then "no space off". The
  words are joined with no spaces and no capital.
- [ ] Press Ctrl+Shift+F11. You hear "Español." once. Press it again: you hear
  "English." once. Say "switch to Spanish", then "cambiar a inglés": the same
  two words, once each. Restart the program: it starts in the language you
  left it in.

### Live transcripts

- [ ] Press Ctrl+Alt+Shift+PageDown. A new untitled document opens and you hear
  "Live transcript on, in a new document." The first time ever, you then hear
  "Please record other people only when they have agreed." Start a second
  transcript later: that sentence is not said again.
- [ ] Talk for a minute with a long pause in the middle. No tone or read-back
  after each phrase; the pause starts a new paragraph. The status bar says
  "Live transcript:" with minutes and words, and Alt+F9 says the same.
- [ ] Switch to another document and keep talking. Nothing is announced in the
  document you are working in, and the words land at the end of the transcript.
- [ ] Press Ctrl+Alt+Shift+PageDown again. You hear "Live transcript stopped,"
  and the number of words, once. The transcript stays open and unsaved.

### Dictation Context

- [ ] Press Ctrl+Alt+Shift+PageUp. The Dictation Context window opens with
  focus in "This document is:", and its title is read once. Tab reaches "Start
  from a saved context:", "Also save it as a context named:" and the read-only
  "Who uses it:" box, each with its own name. Escape closes it and returns you
  to the document.
- [ ] With Moonshine or Whisper chosen, the window says plainly that this
  engine cannot use the context.

### Dictation Status

- [ ] With dictation off, press Alt+F9. You hear "Dictation is off." with the
  engine and the language, once.
- [ ] With dictation on and "caps on" said, press Alt+F9. You hear "Dictation
  on," the engine, the language and "Caps on." In QUILL Lite, Tools > Dictation
  > Dictation Status does the same. In QUILL, while Locked Dictation is
  recording, Alt+F9 still answers for Locked Dictation.

### Dictate Anywhere, in Quill Inkwell

- [ ] In QUILL Lite, open More Dictation Settings and press Dictate in Other
  Programs (Alt+O). Quill Inkwell starts and, with no key chosen yet, the
  Dictate Anywhere Key chooser opens with focus in it.
- [ ] Choose a key, go to a text field in your web browser, press the key and
  dictate a sentence. It is typed at the cursor. The read-back is a tone only,
  and your screen reader's typing echo is the only speech you hear for the
  words.
- [ ] In the browser field, say "scratch that": the phrase is erased. Say
  "select" and a word: you hear "That works in QUILL's own documents. In
  another program, say the words again, or scratch that."
- [ ] Move to a password field and press the key. You hear "That is a password
  field, so nothing is typed there." and nothing is typed.
- [ ] Press the key while QUILL or QUILL Lite is in front: you hear "This is a
  QUILL window: press Ctrl+F11 to dictate here."
- [ ] In Inkwell, the Dictation menu reads Dictate Anywhere as a checked or
  unchecked item, and Dictation Settings (Ctrl+Alt+D) opens the same window the
  editors use.
- [ ] (2026-10-17) In Inkwell, open Dictation Settings (Ctrl+Alt+D), then More
  Dictation Settings (Alt+A). Tab through the whole window: there is no "Allow
  polishing my dictation with AI" box, every other box still answers to its
  Alt letter, and Alt+G does nothing. In QUILL's More Dictation Settings the
  box is still there on Alt+G. With polishing on in QUILL and sharing on,
  choose Clean in Inkwell's Dictation style and press OK: QUILL's Review
  Dictation still offers Polish.

## The October 11 Integration

Checks for the work that landed together on 2026-10-11. Test a source build
from that date or later.

### Show notes and links (Radio and Cast)

- [ ] In Quill Radio, find a podcast episode whose notes have apostrophes or
  quotes (most WordPress-hosted shows do). Station Details reads them as
  words. You should never hear "ampersand number 8 2 1 7".
- [ ] On that episode row, press the Applications key. **View Show Notes...**
  is there. Choose it: Cast's Show Notes window opens, Tab moves between the
  links, and Links in These Notes lists them.
- [ ] Ask for View Show Notes on a second episode. The same window comes back
  with the new notes; a second copy does not open.

### Settings search marks what is greyed out

- [ ] In any Preferences window with Find a setting, type a word that matches
  a setting that is currently unavailable. Its row ends in "(disabled)".
- [ ] Press Enter on that row. You hear "This setting is disabled" and focus
  stays in the search, rather than landing on a control you cannot change.

### Feed checks you can follow and stop

- [ ] In Cast, open the command palette and run Podcasts: Check All Feeds
  Now. You hear the count up front, for example "Checking 42 feeds...".
- [ ] The Feed Refresh Progress window opens. Its status list and progress bar
  are both named when you Tab to them ("Feed refresh status and active
  podcasts", "Feed refresh progress").
- [ ] Press Stop (Alt+S). The check stops and the end sentence says how far it
  got. Closing Cast during a check is silent.
- [ ] Ask for Check All Feeds Now again while one is running. You are told a
  check is already in progress; a second one does not start.

### Cast opens before the library has finished loading

- [ ] With a large library, start Cast. The window appears at once with a
  loading status, and the library fills in shortly after.
- [ ] On a fresh profile, the welcome appears only once the library has
  loaded, not over an empty window.

### QUILL Lite's default document folder

- [ ] Preferences: **Default document folder** has a text field and a
  **Choose default folder...** button, both read with their labels.
- [ ] Leave it blank and open a new document's Save As: the dialog starts in
  your Documents folder. Set a folder, and Open and Save As start there.

### Inkwell saves preferences without a pause

- [ ] In Quill Inkwell, change several menu preferences quickly. Each takes
  effect at once, with no stall.
- [ ] Quit Inkwell and start it again: the last choice you made is the one
  that stuck.

### Your own Gemini key

- [ ] In the own-key dialog, the provider choice offers Google Gemini beside
  OpenAI, and the help under it says a Gemini key also works with Ask About
  an Image.

### Dictation: a slow phrase, then its read-back (2026-10-13)

With a large model and **Tick while a phrase is being worked on** checked, say
a long phrase and wait. Check on NVDA, JAWS and Narrator:

- [ ] NVDA: after four seconds you hear "Still working on that phrase."; when the
  text arrives, its read-back cuts that sentence short rather than waiting
  behind it, and nothing the screen reader was saying of its own is cancelled.
- [ ] JAWS: the same.
- [ ] Narrator: the same.
- [ ] With **What you hear after each phrase** set to words only: no tick, and
  the sentence at four seconds, on each slow phrase.

## QUILL Transcribe Into Other Programs (D-4, 2026-10-15)

An automated test (`tests/integration/test_transcribe_targets.py`) types the
same phrases into each program below and reads the text back, and its results
are the table in QUILL Transcribe's user guide, "Programs it has been tested
with". It can tell whether the keys arrived. It cannot tell what your screen
reader said, so these checks are for that, and for the programs the test has
not reached yet.

Before you start:

- Dictate only into a new, empty document, or a new message addressed to
  nobody. Never into anything you would mind losing or sending.
- Use QUILL Transcribe's defaults: the start and stop key is
  Alt+Shift+Backslash, and **What you hear after each phrase** is a tone.
- Say the same thing each time: "Hello everyone period this is a test comma
  of dictation period new line numbers like forty two arrive intact period".
- Write down the program's version (Help > About) beside anything that goes
  wrong, and whether letters went missing, came out of order, or turned into
  the program's own shortcuts. A program that drops keys is what decides the
  per-program fallback (D-3).

In each program, with each screen reader, all of these must hold:

1. Pressing Alt+Shift+Backslash plays the start tone, and the reader says
   nothing extra: no "c", no stray letter.
2. The text arrives exactly as said, with its capitals, commas, full stops,
   the line break and "42".
3. After each phrase you hear the tone and nothing else: the reader does not
   say "period" or the last letter typed.
4. Switch **What you hear after each phrase** to words: the reader, or QUILL
   Transcribe, reads the phrase once, not twice.
5. Press Alt+Tab to another program while dictating and say a phrase: you hear
   "Dictation paused", nothing is typed in the other program, and choosing
   Resume from the tray menu types the held words back in the first field.
6. "scratch that" takes back the last phrase and nothing before it.

Then check a box for each program and reader once all six held:

- [ ] Notepad with NVDA.
- [ ] Notepad with JAWS.
- [ ] Notepad with Narrator.
- [ ] WordPad with NVDA (Windows 10, or Windows 11 before version 24H2, which
  removed it).
- [ ] WordPad with JAWS.
- [ ] WordPad with Narrator.
- [ ] Word with NVDA. Word's own curly quotes and capitals are fine; a doubled
  capital or a lost space is not.
- [ ] Word with JAWS.
- [ ] Word with Narrator.
- [ ] Outlook with NVDA, in the body of a new message addressed to nobody. No
  letter may act as a shortcut: the message must never send, and the To line
  must stay empty.
- [ ] Outlook with JAWS.
- [ ] Outlook with Narrator.
- [ ] Edge with NVDA, in a multi-line text box with the reader in focus mode.
  Then start dictation once with the reader in browse mode instead, and write
  down what happened: whether the words arrived, or the letters moved you
  around the page as quick-navigation keys. That decides what the user guide
  tells people to do.
- [ ] Edge with JAWS (forms mode in place of focus mode).
- [ ] Edge with Narrator (scan mode off).
- [ ] Chrome with NVDA, the same as Edge.
- [ ] Chrome with JAWS.
- [ ] Chrome with Narrator.
- [ ] Firefox with NVDA, the same as Edge.
- [ ] Firefox with JAWS.
- [ ] Firefox with Narrator.
- [ ] Visual Studio Code with NVDA, in a new untitled file. A bracket or quote
  typed by dictation must not be doubled by the editor's automatic closing.
- [ ] Visual Studio Code with JAWS.
- [ ] Visual Studio Code with Narrator.

### QUILL Transcribe in the Rest of the Family (release, 2026-10-16)

QUILL Transcribe joins the public family on 1 November 2026. These checks are
for the places the other apps now offer it. Use a build made without
`QUILL_DEV_BUILD`, so you meet what the public will.

- [ ] In QUILL, press Alt+Q. The QuillVille menu reads five rows, each with its
  key: Open Quill Radio (Ctrl+Alt+Shift+F7), Open Quill Weather (F8), Open
  Quill Converter (F9), Open Quill Inkwell (F10) and Open QUILL Transcribe
  (Ctrl+Alt+Shift+F11). Press T: QUILL Transcribe opens, or comes to the front.
- [ ] In Quill Radio, Alt+Q reads four rows, ending with Open QUILL Transcribe
  (Ctrl+Alt+Shift+F10); there is no Inkwell row.
- [ ] In Quill Weather, Quill Converter (Alt+U) and Quill Inkwell, the last row
  is Open QUILL Transcribe on Ctrl+Alt+Shift+F11. In QUILL Transcribe's own
  menu the five rows are QUILL, Radio, Weather, Converter and Inkwell, and it
  does not list itself.
- [ ] The tray menus of Quill Radio, Quill Weather and Quill Inkwell read Open
  QUILL Transcribe after the other Open rows.
- [ ] On a computer without QUILL Transcribe, a portable copy of QUILL: Alt+Q,
  T asks whether to download it. Before 1 November 2026 there is nothing to
  download, so after Yes you hear that it could not be fetched and are offered
  the download page. Nothing is downloaded until you say Yes.
- [ ] In Quill Cast and Quill Radio, Edit reads Dictate Here, Ctrl+F11. On a
  computer without QUILL Transcribe, Ctrl+F11 in Search Stations says "Dictate
  Here needs QUILL Transcribe, which is not installed with this copy." once,
  and nothing else.

### Dictation: the command word and command mode (2026-10-15)

With a microphone, in Notepad, Word and Edge through QUILL Transcribe (strict
mode on), and in a QUILL Lite document. Check on NVDA, JAWS and Narrator:

- [ ] NVDA: "QUILL scratch that" takes the last phrase back, with the short
  rising tone and nothing typed; bare "scratch that" is typed as words in
  QUILL Transcribe and works as a command in QUILL Lite.
- [ ] NVDA: "QUILL pancakes" types nothing; you hear the error sound and "Not a
  command", once; "QUILL type that" then types "pancakes".
- [ ] NVDA: "QUILL command mode" says "Command mode" once; the State field (or
  the Dictation cell) shows Command mode and is not read again on its own;
  eight seconds later a falling tone plays, nothing is said, and the next
  phrase is typed.
- [ ] JAWS: the same.
- [ ] Narrator: the same.
- [ ] F11 in QUILL Lite and the Command Key in QUILL Transcribe: one press arms
  one command (the tone), two presses command mode, a third back to dictation.
- [ ] How often each engine hears "QUILL" as something else (Moonshine tiny,
  Whisper, Windows speech): note any that never match.

### Dictation: review before inserting (D-2, 2026-10-15)

With a microphone, in a QUILL document, a QUILL Lite document and Notepad
through QUILL Transcribe, with an own key or a ChatGPT sign-in. Check on NVDA,
JAWS and Narrator:

- [ ] NVDA: "QUILL review that" opens Review Dictation; the title and the text
  are read by the screen reader and nothing else is said; the text reads by
  line, word and character, and a braille display shows it.
- [ ] NVDA: "QUILL make it shorter" says "Working." once, then a summary of no
  more than two sentences; the reader's speech is not heard as the next
  instruction; "QUILL what changed" repeats it.
- [ ] NVDA: Ctrl+Enter in QUILL and QUILL Lite inserts once, and one Ctrl+Z
  takes it out; in QUILL Transcribe the words are typed into the field you
  started in, and nothing was typed while reviewing.
- [ ] JAWS: the same.
- [ ] Narrator: the same.
- [ ] The consent question appears once, with No as the default; No sends
  nothing and says "Nothing was sent."
- [ ] From the tray, QUILL Transcribe's review window comes to the front rather
  than flashing on the taskbar.
- [ ] End QUILL Transcribe from Task Manager with a review open; on the next
  start it says the review was kept, and Review Dictation brings the words back.

### Dictation: rescue, history, snippet blanks and reading back (D-5, D-8, D-18, 2026-10-16)

With a microphone, in a QUILL document, a QUILL Lite document, and Notepad and
Edge through QUILL Transcribe. Check on NVDA, JAWS and Narrator:

- [ ] NVDA: pause QUILL Transcribe by moving the focus, say two phrases, then
  end it from Task Manager. On the next start it says "2 dictated phrases were
  not written last time and are kept. Recent Phrases, Shift+F11, brings them
  back." once, and Recent Phrases lists them after this run's phrases.
- [ ] NVDA: in Recent Phrases, each kept row is read with its label ("Not
  written, held while paused", the time, the words); Discard says
  "Discarded." once and the list reads the next row; Insert Again types it and
  the row is gone next time.
- [ ] NVDA: with Keep a dictation history on Seven days, close and reopen, and
  the earlier phrases are listed as "Earlier"; Clear History asks with No as
  the default, and Yes says "Dictation history cleared."
- [ ] NVDA: in Edge, "QUILL insert snippet bug report" says the snippet's name,
  its count and "Summary?"; each answer is not typed; after the last blank the
  whole snippet is typed once and the reader echoes it; "QUILL scratch that"
  takes all of it back.
- [ ] NVDA: a choice reads its options; "choose two" picks the second.
- [ ] NVDA: in a QUILL document, "read last sentence", "read last paragraph" and
  "read selection" each say the text once, punctuation by name; "read that"
  after a snippet reads all of it.
- [ ] NVDA: Review Transcript's Type into a Field says "Switch to the field you
  want." and types the selection, or all of it, in the field.
- [ ] JAWS: the same.
- [ ] Narrator: the same.

### AutoCorrect and Enter in a list (todo items 38 and 40, 2026-10-16)

In QUILL and in QUILL Lite, each in a new `.txt` document and a new `.md`
document. Turn on **Correct common misspellings as I type** (QUILL: Settings,
Editing; QUILL Lite: Preferences, with Autocorrect while typing on in
Customize Features). Check on NVDA, JAWS and Narrator:

- [ ] NVDA: type `I saw teh` and a space. The reader echoes the space, then
  the word-corrected sound plays and "Corrected to the" is said once. Read the
  line: it says "I saw the".
- [ ] NVDA: press Ctrl+Z straight away. Read the line: "I saw teh", no space.
  Type a space: nothing is said about a correction and the word stays; the
  status bar says "Kept teh as you typed it".
- [ ] NVDA: type `Teh` at the start of a line and a space: "Corrected to The".
  Type `TEH` and a space: no correction.
- [ ] NVDA: type `teh.example.com` and a space, then `adress@example.com` and
  a space: nothing is corrected and nothing is said.
- [ ] NVDA: open a `.py` file and type `teh` and a space: nothing is corrected.
- [ ] NVDA: press Alt+Shift+9. The reader says "AutoCorrect Entries" and the
  focused row of the Corrections list ("abscence becomes absence, built in").
  F1 says what the window is for, then the list's help. Type `teh` in Find
  (Alt+F): the list narrows and the row is read when you Tab back to it.
- [ ] NVDA: Add a correction (`qill`, `QUILL`): the AutoCorrect Entry window's
  two fields and checkbox are read with their labels; OK says "Added: qill
  becomes QUILL" once. Turn Off on `teh` says "Turned off: teh will no longer be
  corrected"; the button is then read as "Turn On". Remove on `teh` says
  "Restored the built-in correction: teh becomes the". Close with Escape and
  type `qill` and a space in the document: "Corrected to QUILL".
- [ ] NVDA: in the `.md` document type `1. bread milk`, put the cursor before
  `milk` and press Enter. "Continued list item" is said once; read the two
  lines: "1. bread", "2. milk". Ctrl+Z puts back the single line.
- [ ] NVDA: on an empty `2. ` item press Enter: "Exited list" once, and the
  marker is gone.
- [ ] NVDA: in the `.txt` document, `1. one` and Enter starts a plain new line
  and says nothing; with **Continue lists in plain text** on, the same Enter
  says "Continued list item" and the new line starts `2. `.
- [ ] NVDA: QUILL Lite Preferences: both new checkboxes are read with their
  labels and states, Tab reaches them, and F1 on each reads its help.
- [ ] JAWS: the same.
- [ ] Narrator: the same.

### QUILL Transcribe: holding the key, the wake phrase and braille (D-9, D-6, 2026-10-15)

With a microphone, in Notepad, Word and Outlook through QUILL Transcribe, and a
braille display where one is available. Check on NVDA, JAWS and Narrator:

- [ ] NVDA: with Hold the dictation key to talk on, hold Alt+Shift+Backslash,
  say two phrases, let go: both are typed after you let go, none arrives as an
  Alt shortcut, and dictation stops. A quick press still turns it on and off.
- [ ] NVDA: with the wake phrase on, the tray says Listening for your wake
  phrase while Notepad is in front; ordinary speech types nothing; "Quill
  dictate dear Sam" starts dictation and types "Dear Sam". With QUILL Lite in
  front, Ctrl+F11 in QUILL Lite starts its own dictation rather than being
  refused.
- [ ] NVDA with a braille display: "Hearing: ..." appears while you speak in
  Outlook, is not spoken, and does not fight the reader's own messages; Command
  mode appears on the display when the Command Key is pressed twice.
- [ ] NVDA: Alt+F9 in the window, and a Dictation Status Key chosen in the File
  menu pressed in Outlook, say one sentence with the state, the program, the
  model and the held count.
- [ ] NVDA: with dictation paused, a Resume Key pressed back in the first field
  types the held words; a Discard Held Words Key throws them away.
- [ ] JAWS: the same.
- [ ] Narrator: the same (Narrator brailles what is spoken, so the braille-only
  lines may not appear).

### QUILL Transcribe: the six moments, on every reader (B-6, 2026-10-16)

The dictation benchmark (the design record's section 26) measures the words
and how fast they arrive. It cannot hear your screen reader, so these are the
checks it leaves to you. Use a microphone, QUILL Transcribe's defaults, and a
new, empty Notepad document. Each moment must be announced once, in plain
words, and the reader must not repeat what QUILL Transcribe already said.

1. **Start.** Press Alt+Shift+Backslash: the start tone plays and you hear
   "Dictation on." once. The reader says no stray letter.
2. **Stop.** Press Alt+Shift+Backslash again while you are still speaking: the
   phrase you were saying is still typed, then you hear "Dictation off." once.
3. **Pause.** While dictating, press Alt+Tab to another program and say a
   phrase: you hear "Dictation paused." and the reason, once; nothing is typed
   in the other program; Resume in the tray menu types the held words in
   Notepad and says how many phrases it wrote.
4. **Refusal.** Start dictation in a password field (a browser sign-in page you
   do not submit), then in QUILL Lite: you hear "That is a password field, so
   nothing is typed there." and "This is a QUILL window: press Ctrl+F11 to
   dictate here." Each is said once, and nothing is typed.
5. **Command mode.** Say "QUILL command mode": you hear "Command mode" once;
   the next phrase is a command, not typed; after eight seconds of quiet a
   falling tone plays and nothing is said.
6. **Review surface.** Say "QUILL review that" (with an AI engine set up): the
   Review Dictation window opens; the reader says its title and the text, and
   QUILL Transcribe says nothing over it; closing it puts you back in
   Notepad.

Check a box once all six held, and write the reader's version beside it:

- [ ] All six with NVDA.
- [ ] All six with JAWS.
- [ ] All six with Narrator.

## Reading guarded documents, Word names in Save As, and typing names in lists (2026-10-16)

Items 37, 41 and 45 of the editor and media completion checks. The code and
its automated tests are done; none of the checks below has been tried with a
screen reader yet.

### Read-Only Guard (QUILL and QUILL Lite)

1. **Toggle.** Open a saved document, press Ctrl+Alt+Backspace: you hear
   "Document is read-only" once, and nothing else. Type a letter: nothing is
   typed and the reader says nothing odd. Press it again: "Document is
   editable".
2. **A refused command.** With the guard on, press Ctrl+V (QUILL Lite) or
   insert a snippet (QUILL): you hear "Document is read-only" once and no
   success sentence follows.
3. **Remembered.** Turn it on, close the app, double-click the same file in
   File Explorer: it opens locked (type a letter to check), with no extra
   announcement beyond the usual open.
4. **Reading still works.** With the guard on, use Find, Go To, the next
   heading key, set a bookmark (QUILL Lite Ctrl+Shift+B, then F2) and add an
   inline note (Alt+Shift+I): each works and says what it normally says. The
   note is offered only as a note kept beside the file.
5. **QUILL Lite menu.** Tools > Read-Only Guard reads as a checked or
   unchecked item with Ctrl+Alt+Backspace beside it.
6. **A long book.** Open a very long Markdown book, turn the guard on, and move
   by heading in browse mode: each heading is read promptly.

- [ ] All six with NVDA.
- [ ] All six with JAWS.
- [ ] All six with Narrator.

### Save As by typed name

1. **QUILL.** In an untitled document, Save As `minutes.docx`: you hear the
   "Saved as minutes.docx, Word format" sentence; open the file in Word and
   move by heading.
2. **QUILL Lite.** Save As `minutes.docx`: one message box saying QUILL Lite
   cannot save Word documents, naming Rich Text; Enter closes it and focus
   returns to the document. Nothing is written.
3. **QUILL Lite, rich document.** In a rich text window, Save As
   `minutes.docx`: the same message, and no "removes all formatting" question
   first.

- [ ] All three with NVDA.
- [ ] All three with JAWS.
- [ ] All three with Narrator.

### Typing a name in a list

1. **QUILL Lite Snippets** (Ctrl+Alt+Shift+Home) with two snippets whose names
   start the same ("meeting agenda", "meeting notes"): type `meeting notes` at
   an ordinary pace. The reader reads the rows as the selection moves, the
   space does not insert anything, and the list ends on "meeting notes".
   Enter inserts it.
2. **A pause.** Type `mee`, wait two seconds, press Space: the selected row
   opens, as before.
3. **No match.** Type `zzz`: you hear "No match for z" (or the letters typed)
   once, and the selection stays.
4. **QUILL Insert Snippet** with a large library (a few thousand snippets):
   the window opens without a long wait, the line above the list says how many
   matched and that only the first 200 are shown, and typing narrows it.
5. **Manage Abbreviations** (QUILL Lite Ctrl+Alt+A, QUILL Ctrl+Shift+Grave then
   Shift+A, Inkwell Ctrl+M) with a large list: rows read as "name, N of total", typing a few letters in the
   list moves to the abbreviation, and searching keeps the selected row when
   it still matches.

- [ ] All five with NVDA.
- [ ] All five with JAWS.
- [ ] All five with Narrator.

## AI conversations and drive properties (2026-10-17)

Items 44 and 46 of the editor and media completion checks. The code and its
automated tests are done; none of the checks below has been tried with a
screen reader yet, so none is checked.

### AI conversations: recent ten, message list, export

In QUILL's Ask Quill (AI menu, with advanced features shown) and in the AI
Conversation window of both editors (the free AI pad's Have a conversation).
Have a conversation of at least four messages, one reply containing a heading
and a table (ask "Compare tea and coffee in a table, with a heading").

1. **Alt+1 to Alt+0.** In the message box, press Alt+1: you hear "Newest,
   Message 4 of 4, ..." once, and focus stays in the message box with any
   typed text intact. Alt+3 reads the second message. Alt+7 says "There are
   only 4 messages so far. Alt+4 reads the oldest." No beep, no menu opening.
2. **Ask Quill, inside the page.** With focus in Ask Quill's in-page message
   field, Alt+2 reads the second newest message once (not twice).
3. **Message list.** Press Messages... (Alt+G) or Message List...: the list
   opens on the newest row; the row reads "Message 4 of 4, AI: ...". Arrow up,
   press Enter: the reading window opens; H moves by heading, T to the table,
   and table navigation reads the column headers. Escape returns to the same
   row, and the reader says that row, nothing extra.
4. **Read as Text.** On a row, Read as Text: the message as it arrived, in an
   edit field you can arrow through; Escape returns to the row.
5. **Reopen.** Close the list, reopen it: it opens on the row you left.
6. **Export.** Export Conversation... (Alt+X): the Save As window opens with
   "AI conversation.docx". Save, open the file in Word, and move by heading:
   level 2 per message, the reply's heading at level 3, the table as a table.
   Export again to the same name: Windows asks before replacing. Cancel: you
   hear nothing more and focus is back where it was. Export as a .txt and read
   it in Notepad. Your document is unchanged (title bar not marked saved).
7. **Reading position.** In the AI Conversation window, send a long
   question, then Shift+Tab into the Conversation box and arrow to the middle
   before the reply arrives. When the reply is read out, your caret is still
   where you left it.
8. **Fallback list** (only on a computer where Ask Quill shows a plain list):
   Enter on a row opens that message; a new reply does not move your row.
9. **Braille.** Alt+1 shows the message on the braille display the way other
   QUILL announcements appear, without the display flickering.

- [ ] All nine with NVDA (QUILL).
- [ ] All nine with JAWS (QUILL).
- [ ] Steps 1, 3 to 7 and 9 in QUILL Lite's AI Conversation window with NVDA.
- [ ] Steps 1, 3 to 7 and 9 in QUILL Lite's AI Conversation window with JAWS.
- [ ] All nine with Narrator.

### The drive in file properties

1. **Quill Radio.** Local Media, highlight a song on the C drive, Alt+Enter:
   arrow to the end of the box; four lines: "Drive: C:\ ...", capacity, used
   with percent, free. Sizes match File Explorer's This PC view for that
   drive.
2. **A USB stick.** Add a song from a USB stick, Alt+Enter: "removable
   drive". Pull the stick out and press Alt+Enter again: the box opens, says
   "On this computer: no, missing" and one "Drive: not available" line.
3. **A network share.** A song on a mapped or `\\server\share` path: "network
   drive". Disconnect the network and repeat: one "network location could not
   be reached" line; note how long the box takes to open.
4. **Quill Converter.** Highlight a queued file, Alt+Enter: the drive lines
   end the File Properties text.

- [ ] All four with NVDA.
- [ ] All four with JAWS.
- [ ] All four with Narrator.

## PDFs in QUILL Lite: page breaks, Import / Convert, the portable copy (2026-10-17)

The code and its automated tests are done; none of the checks below has been
tried with a screen reader yet. What the code establishes: a PDF's text
reaches the Rich Edit control with one U+000C (form feed) between pages,
directly after the last character of a page and directly before the first
character of the next, in plain mode and after a switch to rich; the Page cell
and Go To's Page list count those characters and show only numbers;
announcements, braille and QUILL Lite's status-bar message now carry a line
break instead. What only listening can establish is what each reader does
with the character itself.

### Page breaks, heard

Open a PDF of three or more pages in QUILL Lite with Ctrl+O (any multi-page
PDF with text). Then:

1. **Arrow across a page.** Ctrl+G, choose Page, pick 2, Enter. Press Up Arrow
   once, then Down Arrow once. Write down exactly what is said on each line:
   is the last line of page 1 read on its own, or run together with the
   first line of page 2? Is anything said for the page break itself ("form
   feed", "page break", a symbol name, a pause, nothing)?
2. **By character.** From the top of page 2, press Left Arrow once and then
   Right Arrow once: write down what is said for the character.
3. **Say All.** From the top of page 1, read continuously across into page 2:
   is anything extra spoken at the boundary?
4. **Ctrl+Shift+C on it.** Put the cursor on the page break (step 2) and press
   Ctrl+Shift+C: you hear "Page break" and U+000C, not "Unnamed character".
   Ctrl+Alt+C opens the details window saying one page ends there.
5. **An announcement across it.** Select from the middle of the last line of
   page 1 to the middle of the first line of page 2 (Shift+Down Arrow), then
   use a command that quotes the selection's start (for example Edit >
   Selection > Review Buffer, Alt+Shift+U). Nothing says "form feed".
6. **The status bar.** After step 5, press Insert+Page Down (JAWS) or read the
   status bar (NVDA: Insert+End): no control-character name.
7. **The Line cell.** On the first line of page 2, compare the status bar's
   Line number with the line count you would expect: if Rich Edit draws the
   page break as a line of its own, the two may differ by one per page. Note
   it if so.
8. **Rich mode.** Switch the PDF to rich text with Format > Switch Document
   Mode (Alt+Shift+F, until it says rich text): repeat steps 1 and 2.

- [ ] All eight with NVDA.
- [ ] All eight with JAWS.
- [ ] Steps 1 to 4 with Narrator.
- [ ] Repeat steps 1, 2 and 4 in QUILL (File > Open on the same PDF).

### Import / Convert Document in QUILL Lite

1. **The row.** Alt+F: the File menu has "Import / Convert Document (OCR)..."
   after "Open from URL...", with no key shown; I selects it.
2. **A Word file.** Choose a .docx: you hear "Converting name.docx", then
   "Opened name.docx as editable text, read by QUILL's own Word reader.
   Nothing was uploaded." The title is "name (converted)", and closing asks to
   save.
3. **A busy window.** With text in the window, import again: a new window opens
   with the result and your text is untouched.
4. **A scanned PDF.** Choose a scanned PDF: the question box names QUILL Lite,
   Yes is the default, Escape cancels and nothing opens. Yes: "Reading
   name.pdf with OCR on this computer", the status bar counts pages, and the
   result is announced once.
5. **A photo of a page.** Choose a .jpg of printed text, on a computer without
   Tesseract: it is read with Windows OCR, no question.
6. **Cancel the box.** Escape in the file box: nothing is said.

- [ ] All six with NVDA.
- [ ] All six with JAWS.
- [ ] All six with Narrator.

### The portable copy, after the next build

These need the next real portable build (see
`docs/building-windows-family.md`, "QUILL Lite portable: the PDF reader and
OCR").

1. Unzip QuillLite-Portable on a computer with no QUILL installed, start
   QuillLite.exe, Ctrl+O a text PDF: it opens with its pages, not "This copy
   of QUILL Lite has no PDF reader".
2. Ctrl+O a scanned PDF and answer Yes: Windows OCR reads it.
3. File > Import / Convert Document on a .png of text: it is read.

- [ ] All three, any one screen reader.

## Spanish review (for a native speaker)

Not a screen-reader check: questions for a native Spanish speaker, to answer
before the drafted Spanish commands are switched on for everybody. Until then
they work only in a development build with `QUILL_DICTATION_SPANISH_COMMANDS=1`,
and Spanish dictation uses the English commands. The full drafted table is
`quill/core/windows_dictation/vocabulary_es.py`; the design record's section 9
explains each choice. For each item, say whether a Spanish speaker would say
it naturally, and what you would say instead.

- [ ] **"Polish that" (2026-10-17).** Drafted as "QUILL pule eso", "QUILL
  púlelo" and "QUILL mejora eso". It asks the AI to tidy punctuation, capital
  letters and small slips in a phrase in Review Dictation, keeping the words.
  Is "pulir" the word you would use for that, or does "mejora eso" (or
  something else, such as "arregla eso") sound more natural? "Corrige eso" was
  avoided because "corrige" followed by words already means "correct these
  words".
- [ ] **"Yes" and "no" to "Add a correction?" (2026-10-17).** In QUILL
  Transcribe, after you correct the same word the same way twice, dictation
  asks (in English) whether to remember the correction, and you answer after
  the command word. Drafted as "QUILL sí" and "QUILL no". Would you say "sí",
  or something longer such as "sí, añádela" or "vale"? Should "vale" or
  "claro" count as yes?
- [ ] **The wake and stop phrases**, "Quill dicta" and "deja de dictar".
- [ ] **The punctuation words** ("coma", "punto", "punto y aparte", "abrir
  interrogación" and the rest), as listed in Dictation Commands.
- [ ] **The command table** (`SPANISH_COMMAND_HELP` and `SPANISH_PREFIX_HELP`),
  from "borra eso" to "inserta fragmento".

## Highlighted passages, chapters for any recording, and feed position (todo 39, 42, 43; 2026-10-16)

Nothing here was checked off from source inspection; every item needs a real
reader. Use a `.docx` with three highlighted passages in different colours
(yellow, pink, teal), one inside a table.

### Highlighted passages (QUILL and QUILL Lite)

1. **QUILL, Word document edited as Rich Text.** Alt+Page Down: you hear
   "Yellow highlight, 1 of 3: ..." once, and the reader does not also repeat
   the whole line unasked. Alt+Page Up from the first wraps to the last.
2. **Describe Formatting** (Ctrl+Shift+D) inside a highlighted word says
   "..., yellow highlight"; outside one it does not mention highlighting.
3. **Ctrl+F2** opens Highlighted Passages on the passage the cursor is in;
   rows read words first, then colour, then "in:" and the paragraph. Enter
   lands on the passage (the reader reads that line); Escape returns with the
   caret unmoved; Alt+Left returns after Enter.
4. **Apply and remove.** Format > Highlight > Pink on a word, then Ctrl+F2:
   it is listed. Ctrl+Shift+N on it: it is gone. Save, reopen: the colours are
   the ones you saved (pink stays pink).
5. **QUILL Lite, the same `.docx`** (opened read-only as text): the three
   keys behave as above, the table cell's passage included.
6. **Braille.** With a braille display, the arrival sentence appears as a
   flash message and the display then shows the line at the passage, cursor
   on its first character.

- [ ] All six with NVDA.
- [ ] All six with JAWS.
- [ ] Items 1, 3 and 5 with Narrator.

### Find Chapters in a Recording (QUILL, Quill Studio)

1. QUILL: Tools > Speech > Find Chapters in a Recording... on a 30-minute MP3
   with no chapters. The silence window opens on top of the Workbench; after
   OK you hear "Proposing chapters from silences started" and, later, the
   count. Rows read "Proposed chapter 1 ...".
2. Press the button again during a scan of a long recording (an hour or
   more): it reads "Stop proposing chapters" while running and you hear the
   stopped sentence; the list is unchanged.
3. A recording with chapters: the Keep / Replace question reads both choices;
   Enter keeps.
4. Quill Studio: Studio > Find Chapters in a Recording... (Ctrl+Shift+R), and
   Edit a Book (Ctrl+E) now opens; Ctrl+Shift+T and Ctrl+Shift+Q work inside
   the Workbench while a book plays.

- [ ] All four with NVDA.
- [ ] All four with JAWS.

### Browse Stations categories and podcast position

1. Quill Radio Browse Stations: open By Country > Ireland, arrow onto a
   station, Escape: focus is on "Ireland", folded; Escape again: "By Country";
   Escape again closes. Playback continues throughout; a query in the Find box
   is still there when you Tab back to it.
2. Apple country rows read "..., Apple chart for this country, any language".
3. QUILL Cast: Favorites > Enter on a podcast, arrow to its fifth episode,
   Backspace, Enter again: the cursor is on the fifth episode. Close and
   reopen Cast: still there. Refresh the podcast: still there.
4. QUILL's Podcast Manager: choose a podcast, arrow to an episode, close the
   window, open it and choose the podcast again: the same episode is
   selected and read.

- [ ] All four with NVDA.
- [ ] All four with JAWS.

## QUILL Lite Word Documents and Table Navigation (2026-10-17)

Real `.docx` files, made in Word: one plain (headings 1 to 6, a list, bold, a
link), and one with a table and a comment.

1. QUILL Lite, Ctrl+O, the plain file: "Opening ..." then "Opened as Rich
   Text. Headings and bold are shown formatted." Ctrl+Alt+H walks Heading 1 to
   Heading 6 with their levels.
2. Type a line, Ctrl+S: "Saved ...". Open it in Word: headings are still
   headings in the navigation pane; nothing grey in dark mode.
3. The file with a comment: the Open Word document window reads its sentence
   and the first row; Escape opens it as text, and Ctrl+S offers Save As.
4. Open it again, choose Edit as Rich Text, Ctrl+S: "Backed up the original to
   ..." then "Saved ..."; the backup opens in Word with the comment.
5. A long document: Ctrl+S twice quickly: the second says "Still saving ...".
6. In the table: Ctrl+Alt+Right, Down, Alt+Home, Ctrl+Alt+End read "Row N of
   M, column C of D: text"; past the edge, "No more cells"; outside, "Not in a
   table". Note whether the screen reader takes Ctrl+Alt+arrows first.
7. QUILL: the same file opens with the same question in the same words.

- [ ] All seven with NVDA.
- [ ] All seven with JAWS.


### Word-level review, AI retries, the note-line cue, and browse M and F (2026-10-17)

1. QUILL and QUILL Lite: select a paragraph, ask the free AI to Rewrite it, and
   choose Review Changes in the AI Result window. On a change with several word
   edits, Alt+W reaches "Words in this change"; each row reads the edit and its
   sentence. Space on one row says only its state (nothing else spoken). Apply
   Checked: the dropped word stays as it was, and you hear "Applied 1 change, 1
   of them in part, as one undo step". Ctrl+Z takes the whole edit back.
2. In the same window, uncheck every row of one change: you hear "No word edits
   left in this change, so it will not be applied", and the Changes row is
   unchecked when you Alt+C back to it. Check one row again: "This change will
   be applied again". Accept All gives exactly the AI's text.
3. A one-word change shows no Words list and Tab goes from Changes to Change
   details. F1 on the Words list reads its help.
4. With a network that drops or a service answering busy (a developer can point
   the service at a test server that answers 503 twice): the answer arrives
   after a short wait and nothing is said about the retries. With a server that
   answers 503 three times: one failure sentence, said once.
5. QUILL and QUILL Lite: add an inline note to a line, go to the top, and arrow
   down: the two-tap sound plays on that line only, once; Left, Right, Home and
   End on that line are silent. Next Inline Note to it plays no tap.
6. Settings > Editing (QUILL) and Preferences (QUILL Lite), "When the caret
   reaches a line with an inline note": Say "note" speaks the word once on
   arrival; Nothing is silent. With a braille display and the sound chosen,
   "note" flashes on the display without being spoken.
7. QUILL: open a PDF with several pages, lock Quick Nav (Ctrl+Shift+Grave
   twice): F says "Page 2 of N"; Shift+F from mid-page goes to the top of the
   page; the cheat sheet (?) lists M and F. Press Escape and arrow down across
   a page break: "Page 3 of N" is said once, and not again on the next arrows.
8. QUILL: in a document with typing mistakes, Quick Nav M selects the next
   misspelled word and says "Misspelled: word, line N"; Shift+M goes back; in
   a clean document M says there are none.

- [ ] All eight with NVDA.
- [ ] All eight with JAWS.
- [ ] Checks 1, 5 and 7 with Narrator.

## Word documents in installed copies, and GLOW audits (2026-10-17)

Before 2026-10-17 the shared runtime left out lxml, so an *installed* QUILL or
QUILL Lite opened every `.docx` as plain text and could not save one, and the
GLOW audits failed. These checks need the first installers built after that
change (see *Rebaselining after the Word support change* in
`docs/building-windows-family.md`). Use the two Word files from the section
above.

1. Installed QUILL Lite (from its installer, not the portable ZIP): Ctrl+O, the
   plain file. You hear "Opened as Rich Text. Headings and bold are shown
   formatted.", not the file as text. Type a line, Ctrl+S, "Saved ...", and the
   file opens in Word with its headings.
2. Installed QUILL: the same file, the same result.
3. Installed QUILL, with GLOW turned on (Settings > Experimental): **GLOW Audit
   File...** (from the Command Palette) on the Word file, then a PDF,
   then a PowerPoint file. Each produces a report; none says a module is
   missing.
4. Both portable ZIPs, on a computer with nothing installed: checks 1 and 2.
5. In either editor, open an Excel `.xlsx`: it opens as text with "Sheet:"
   headings; Ctrl+S explains why and opens Save As with a `.txt` name.

- [ ] All five with NVDA.
- [ ] Checks 1 and 3 with JAWS.

## Quill Beacon and QUILL Social Menu Keys (D.9, 2026-10-17)

Every menu command in both apps now shows a key, and no two commands in one
menu share an access letter. Start each app from source with an empty data
folder.

1. Quill Beacon: walk every menu with Alt and the arrows. Each row reads its
   name and then its key, for example "Sync Now F9" and "Find Duplicates
   Ctrl+Alt+D"; no row is read without a key, and Help > About says Alt+F1.
2. Quill Beacon: press F9. You hear "Synced. Pushed 0, pulled 0." once, or
   the sync error in a message box if no sync is set up. Ctrl+F9 opens Sync
   Settings, Shift+F9 Sync History and Ctrl+Shift+F9 Auto Sync; Escape closes
   each and focus returns to where it was.
3. Quill Beacon: press Alt+E, then P: duplicates are found (or "No duplicates
   found") without any other Edit item running first. Press Alt+E, then H on
   a selected bookmark: it is archived. Alt+V, then L opens the Command
   Palette, which shows Ctrl+Alt+D beside Find Duplicates.
4. Quill Beacon: Ctrl+Shift+Comma opens Accessibility Settings; Ctrl+Alt+T the
   Trail Editor; Ctrl+Alt+Shift+G the Smart Collections Manager; Ctrl+Alt+I
   the Status Center. With focus in the search box, type ordinary text after
   each: nothing else opens.
5. QUILL Social: walk every menu. Each row reads its key, including Listen >
   Play / Pause (Ctrl+Shift+Space), Next article (Ctrl+Shift+Period) and
   Studio > Drafts... (Ctrl+Shift+D). Note how your screen reader speaks the
   period and comma keys.
6. QUILL Social: open a feed with unread articles, press Ctrl+Shift+L, then
   Ctrl+Shift+Period (the next article starts), Ctrl+Shift+Comma (back one),
   Ctrl+Shift+Space twice (pause, then carry on) and Ctrl+Shift+S (silence).
7. QUILL Social: select a smart folder, press Ctrl+Shift+Delete: the question
   is asked and No leaves the folder. Select a feed, Ctrl+Alt+U: the same.
8. QUILL Social: close the app, change `"drafts": "Ctrl+Shift+D"` in
   keymap.json to `"drafts": "Ctrl+J"`, start it again: Studio > Drafts...
   reads Ctrl+J, Ctrl+J opens Drafts, Ctrl+Shift+D does nothing, and F1 lists
   it.
9. QUILL Social: Alt+I, then K bookmarks the focused post; Alt+D, then T opens
   New smart folder; Alt+T, then L Notification policies; Alt+T, then G
   Plugins.

- [ ] All nine with NVDA.
- [ ] All nine with JAWS.
- [ ] Checks 1, 3, 5 and 6 with Narrator.

## Quill Radio: One File per Song, and Marks in Three More Lists (D.3, 2026-10-17)

Use a music station that sends song names (What's Playing, Ctrl+T, names the
song) and a recordings folder with a few finished recordings in it.

1. Record > Recording Settings... (Ctrl+Alt+Shift+I), Alt+N: the check box
   reads "Split the recording at each song change", not checked; F1 on it
   explains the split and its limit. Check it and choose OK: you hear
   "Recording settings saved".
2. Press Ctrl+R, let at least two songs play, press Ctrl+R again. After a few
   seconds you hear "Split ... into N songs, starting with ...", said once.
   Open Radio Recordings (Ctrl+Shift+R): the songs are there, numbered in
   order, and the long recording is gone. Play two neighbouring songs: no
   music is missing between them.
3. Repeat check 2 on a talk station: you hear "Kept ... as one recording: no
   song change was heard while it recorded."
4. Radio Recordings: arrow to a finished recording and press period. You hear
   "Marked. 1 marked." and the row reads "(marked)" when you arrow away and
   back. Mark a second one, press Delete: the question "Delete 2
   recordings?" has No chosen; Yes says "Deleted 2 recordings." and focus is on
   a real row. Ctrl+Z in the main window brings both back.
5. Radio Recordings: mark one recording, arrow to another and press Enter. It
   plays and you hear, once, "That used the selected row only; 1 row is still
   marked for Delete." Press Enter again: no second explanation.
6. Schedule Recording (Ctrl+Shift+S) with three schedules: mark two with
   period, then Shift+F10: the menu lists Mark for Deleting, Remove 2
   Marked... (Delete) and Clear Marks (Ctrl+Shift+Delete) and no one-row
   Delete. Escape, then Ctrl+Shift+Delete: "Cleared 2 marks." and no row says
   "(marked)".
7. Browse Stations: in your saved YouTube videos (or among favorites), mark two
   rows with period and press Delete: one question, then "Deleted 2 items."
   and the rows are gone. On a country row, period says which rows can be
   marked.

- [ ] All seven with NVDA.
- [ ] All seven with JAWS.
- [ ] Checks 2, 4 and 7 with Narrator.


## Choose Your AI, Which AI and AI Usage, QUILL and QUILL Lite (codex.md 10A, 2026-10-31)

Run each check in both editors. Have the free AI connected and, if you can, a
ChatGPT plan or an own key signed in.

1. Press Ctrl+4. You hear the title "Choose Your AI" and the row in use, such
   as "QUILL's free AI, in use", and nothing else. Arrow down the list: each
   row reads its name and state; the app adds nothing.
2. Tab once: the About line reads what the row can do and who gets the text.
   Tab again: Model. On the free AI it reads "QUILL chooses the model" and is
   unavailable. Tab again: the one button, whose name follows the row (Use
   This, Sign In..., Sign Out). Tab again: Close. F1 on each of the five says
   what it is for.
3. On a signed-in row that is not in use, press Enter. You hear once "Now
   using ..." and the row now reads "in use" when you arrow away and back.
4. On a signed-in row, press Delete. The question "Sign out of ...?" has No
   chosen; Enter changes nothing. Yes signs out and says so once.
5. Close the window. Press Ctrl+8: one line naming the AI in use and its
   model. Press Ctrl+8 twice quickly: Choose Your AI opens and nothing is
   spoken over it.
6. Press F6 and arrow to the AI cell: it reads "AI: ..." matching Ctrl+8.
   Enter opens Choose Your AI.
7. Press Alt+F5 while not signed in to ChatGPT: Choose Your AI opens on "My
   ChatGPT plan" with the sign-in step over it; Escape closes the step and
   nothing is said. Alt+F2 opens the window with Use My Own AI Key over it.
8. Open AI Usage (QUILL Ctrl+Alt+Shift+F2, QUILL Lite Ctrl+Alt+Shift+F9): one
   list, a sentence per AI, focus on the one in use. When the free AI's count
   arrives it is said once.
9. With the free AI in use, open the AI menu: Ask About an Image reads
   "(needs a connection that sees)" after its name and still shows its key.
   Press Ctrl+F5: nothing is sent, the switch question has Yes chosen.
10. Press Ctrl+6: the AI Conversation opens; the About field's first line says
    "Asking ... about this document." Each reply is spoken and brailled.

- [ ] All ten with NVDA, in both editors.
- [ ] All ten with JAWS, in both editors.
- [ ] Checks 1, 3, 5 and 8 with Narrator.


## GitHub Copilot, Codex, Plan Options and Do a Document Task, QUILL and QUILL Lite (codex.md 10A.12, 10A.13, 6.2, 2026-11-01)

Run each check in both editors. Copilot checks need a build with this app's
GitHub registration and a Copilot account (Free and paid if you can); the Codex
checks need a ChatGPT plan and a build with the Codex engine.

1. Ctrl+4, arrow to "My GitHub Copilot". In a build without the GitHub
   registration it reads "not available yet", and Tab to About reads one
   sentence saying why. Nothing is spoken by the app.
2. With the registration, press Enter on the Copilot row. The sign-in step
   opens with Open the Page focused. When the code arrives you hear it once,
   spaced out ("The code is A B C D ... It is on the clipboard."), and the Code
   field reads the same spaced characters. Ctrl+V in the browser pastes it.
3. Approve on GitHub's page. The step closes by itself and you hear once
   "Signed in to My GitHub Copilot. It is now in use." The row reads "in use".
   Press Escape in a fresh step instead: nothing is said and nothing changes.
4. On Copilot Free, Tab to Model: it reads "Auto (Copilot Free chooses)" and is
   unavailable. Press Ctrl+8: one line naming Copilot and GitHub's count, said
   once even when it waits a moment for GitHub.
5. Open AI Usage: the Copilot row says GitHub's count; when it arrives it is
   said once and the selection does not move.
6. Signed in to your ChatGPT plan, arrow to "Codex, for tasks": it reads
   "signed in". Enter: "Now using Codex, for tasks." Ctrl+8 says "Codex, on
   your ChatGPT plan. Single requests go to the plan directly."
7. On the ChatGPT or Codex row, Tab past the action button: Plan Options...
   is there; on any other row it is not. Its window has Allow web search (a
   check box; Space changes it and only your reader speaks) and Forget on This
   Computer. Forget says once that the sign-in was forgotten here.
8. On the free AI, open the AI menu: Do a Document Task reads "(needs Copilot
   or Codex)" after its name and still shows Ctrl+3. Press Ctrl+3: nothing is
   sent and the switch question has Yes chosen.
9. On Copilot or Codex, press Ctrl+3: Do a Document Task opens with focus in
   Instruction and nothing spoken by the app. Shift+Tab reaches Status ("Using
   GitHub Copilot") and Conversation.
10. Type "Make the first heading level 1" and Enter. Allow This Step? opens
    with focus on its sentence, which your reader says. Enter allows once;
    Review AI Changes opens; accept. When the task ends you hear the summary
    once and Ctrl+Z in the document takes the change back in one step.
11. Start a task and press Stop (Alt+T) while it works, or while Allow This
    Step? is open: the question closes, the task ends within a second and you
    hear "Stopped. ..." once. Escape in the window closes it and stops a task.

- [ ] All eleven with NVDA, in both editors.
- [ ] All eleven with JAWS, in both editors.
- [ ] Checks 2, 3, 9 and 10 with Narrator.


## Choose Your AI, Ask and pictures, Quill Radio and QUILL Cast (codex.md Phase 3, 2026-11-01)

Run the Radio checks in Quill Radio and the Cast checks in QUILL Cast. In Cast,
turn AI help on first (Ctrl+, > The window). A ChatGPT plan makes most checks
possible; check 6 and check 12 also want the free AI in use.

Quill Radio:

1. Press Ctrl+Shift+8. Ask opens with focus in Your message, and the window is
   on the Window menu. Shift+Tab to About this conversation: it starts "Asking
   My ChatGPT plan about this station." Nothing is spoken on open.
2. With a station playing, type "What is this song?" and press Enter. You hear
   "Working." and then the reply, once. Wait for the next song and ask again:
   you hear "Now playing changed since your last question." once, before
   "Working."
3. Shift+Tab to Quick questions and arrow through it: nothing is said but the
   rows, and focus stays put. The first nine are Ask QUILL Radio's. Press Enter
   on "Recommend stations like my favorites": focus moves to Your message and
   you hear what will be sent with it. Press Enter on "What can I do here?":
   the answer is read once, ending "Answered on this computer. Nothing was
   sent."
4. Press Ctrl+F8: one line naming the AI in use. Press it twice quickly:
   Choose Your AI opens on the row in use. Press Alt+F5: Choose Your AI opens
   on the ChatGPT row.
5. Press F6 to the status bar and move to the last cell: it reads "AI: ChatGPT
   plan". Enter opens Choose Your AI. Choose another AI there: the cell's text
   follows the next time you read it, and nothing extra is spoken.
6. With the free AI in use, open the Video menu: Describe the Video reads
   "(needs a connection that sees)" and still shows Ctrl+F5. Play a video and
   press Ctrl+F5: nothing is sent and the switch question has Yes chosen.
7. On your ChatGPT plan with a video showing, press Ctrl+F5: you hear
   "Working.", then "Looked at 1 picture ... Described by My ChatGPT plan." and
   the description, once, and a result window opens. Press Ctrl+F5 again
   without the picture changing: the answer comes straight back, ending
   "Nothing was sent".
8. Start Quill Radio with --safe-mode and press Ctrl+Shift+8 and
   Ctrl+Shift+F8: each says "AI is off in Safe Mode." and nothing opens.

QUILL Cast:

9. Select an episode you have started and press Ctrl+Shift+8. About this
   conversation starts "Asking My ChatGPT plan about this episode." The first
   quick question is "What did I miss in this episode?"
10. Help > AI Features: the first three rows are Ask (Ctrl+Shift+8), Which AI
    Am I Using (Ctrl+F8) and Choose Your AI (Ctrl+Shift+F8), each letter works,
    and What Did I Miss in This Episode? (D) is near the end. In an episode
    list, Ctrl+4 still runs Quick Action 4, and Ctrl+2 still reaches window 2.
11. Choose What Did I Miss in This Episode? on an episode you have started: the
    answer is read once and shown in the answer window. On one you have not
    started you hear that there is nothing to miss, and nothing is sent.
12. With the free AI in use, on an episode whose show notes have a described
    picture, press Ctrl+Alt+F5: the switch question comes first; answer No and
    the notes' own description is read.
13. On your ChatGPT plan, press Ctrl+Alt+F5: the chooser lists the artwork and
    the show-note pictures by name, then "A picture file on this computer...".
    Choose the artwork: you hear "Fetching the picture.", "Working.", then the
    description, once.
14. The status bar's last cell reads "AI: ChatGPT plan"; with AI help off it
    reads "AI: off".

- [ ] All fourteen with NVDA.
- [ ] All fourteen with JAWS.
- [ ] Checks 1, 4, 9 and 13 with Narrator.

## Choose Your AI, Ask and pictures, QUILL Studio and QUILL Transcribe (codex.md Phase 3, 2026-11-01)

Run the Studio checks in QUILL Studio and the Transcribe checks in QUILL
Transcribe. A ChatGPT plan signed in for each app makes most checks possible;
Studio check 6 also wants the free AI in use, and Transcribe check 12 wants a
copy that has never signed in to ChatGPT as QUILL Transcribe.

QUILL Studio:

1. Press Alt+A. The AI menu reads Ask (Ctrl+6), Which AI Am I Using (Ctrl+8),
   Choose Your AI (Ctrl+4), Describe a Picture (Ctrl+F5), Use My ChatGPT
   Subscription (Alt+F5), Use My Own AI Key (Alt+F2), AI Usage
   (Ctrl+Alt+Shift+F2), Privacy Agreement (Alt+Shift+F2) and Set Up AI
   (Ctrl+Alt+Shift+A). Each letter works. The Capture menu no longer has a
   ChatGPT row.
2. If Studio was signed in to your ChatGPT plan before this build, press
   Ctrl+8: it names My ChatGPT plan without asking you to choose again. Press
   it twice quickly: Choose Your AI opens on that row, and nothing is spoken
   on open.
3. Press Ctrl+6. Ask opens with focus in Your message. Shift+Tab to About this
   conversation: it starts "Asking My ChatGPT plan about your recording setup."
   The first two quick questions are "Is my setup ready?" and "Does this
   recording look right?".
4. Run a demonstration check in Record a Demonstration, close it, then ask "Is
   my setup ready?": the answer refers to what the check found. You hear
   "Working." and the reply, once.
5. Press F6 to the status bar and move to the last cell: it reads "AI: ChatGPT
   plan". Enter opens Choose Your AI.
6. With the free AI in use, open the AI menu: Describe a Picture reads "(needs
   a connection that sees)" and still shows Ctrl+F5. Press Ctrl+F5: nothing
   opens, nothing is sent, and the switch question has Yes chosen.
7. On your ChatGPT plan, press Ctrl+F5 for the first time: you hear "Pictures
   you ask about in QUILL Studio go to OpenAI on your ChatGPT plan. Nothing is
   sent until you ask." with No chosen. Choose Yes, pick a picture: you hear
   "Working.", then "Looked at 1 picture ... Described by My ChatGPT plan." and
   the description, once, and a result window opens. Press Ctrl+F5 on the same
   picture: no consent question, and the answer ends "Nothing was sent".
8. Press Ctrl+F5 and pick a video, type 1:30 and press Enter: the description
   names 1:30.
9. In the Screenshot Inspector, choose Ask AI: the confirmation names My
   ChatGPT plan and says it goes to OpenAI on your ChatGPT plan. No is chosen.
10. Start Studio with --safe-mode and press Ctrl+6, Ctrl+4 and Ctrl+F5: each
    says "AI is off in Safe Mode." and nothing opens.

QUILL Transcribe:

11. Press Alt+A. The AI menu sits after Options and reads Ask (Ctrl+Shift+8),
    Which AI Am I Using (Ctrl+F8), Choose Your AI (Ctrl+Shift+F8), Use My
    ChatGPT Subscription (Alt+F5), Use My Own AI Key (Alt+F2), AI Usage
    (Ctrl+Alt+Shift+F2) and Privacy Agreement (Alt+Shift+F2). Ctrl+2 still
    reaches window 2 on the Window menu.
12. On a copy that has never signed in as QUILL Transcribe, with the free AI in
    use, open Review Dictation (Shift+F4): you hear once "QUILL Transcribe now
    signs in to your AI on its own and no longer uses QUILL's sign-in; press
    Ctrl+Shift+F8 to sign in as QUILL Transcribe." The Status line starts with
    the same sentence, then says why the AI cannot change the words. Close and
    open it again: the sentence is not said again.
13. Press Ctrl+Shift+F8, sign in to My ChatGPT plan: the browser page names
    QUILL Transcribe, not QUILL. You hear "Signed in to My ChatGPT plan. It is
    now in use." once.
14. Tab through the main window to the AI line: it reads "AI" and "AI: ChatGPT
    plan", and F1 says Enter opens Choose Your AI. Press Enter: it opens.
15. Open a finished transcript from Notifications, close it, and press
    Ctrl+Shift+8. Ask "What was decided?": the answer is about that
    transcript. About this conversation starts "Asking My ChatGPT plan about
    your dictation."
16. Start QUILL Transcribe with --safe-mode and press Ctrl+Shift+8 and Ctrl+F8:
    each says "AI is off in Safe Mode."

- [ ] All sixteen with NVDA.
- [ ] All sixteen with JAWS.
- [ ] Checks 1, 7, 11 and 12 with Narrator.

## Choose Your AI, Ask and first features, Quill Weather, Quill Converter, Quill Media Player, Quill Inkwell and QuillBeacon (codex.md Phase 3, 2026-11-01)

Run each app's checks in that app. A ChatGPT plan signed in for each app makes
most checks possible; the checks that offer a switch want the free AI in use.
Each app signs in on its own, so the browser page should name that app, for
example QUILL Weather, never QUILL.

Every app:

1. Alt+I (Alt+A in QuillBeacon, the Assist menu) opens the AI rows, and every
   row reads with its key. In Weather, Converter, Media Player and Inkwell the
   keys are Ask Ctrl+Shift+8, Which AI Ctrl+F8 and Choose Your AI
   Ctrl+Shift+F8, and Ctrl+2 still reaches window 2 on the Window menu. In
   QuillBeacon they are Ctrl+6, Ctrl+8 and Ctrl+4.
2. Which AI says one line; pressed twice quickly it opens Choose Your AI, focus
   in the list on the row in use.
3. Tab to the AI line in the main window: it reads "AI" and the AI in use, F1
   says Enter opens Choose Your AI, and Enter opens it.
4. Start the app with --safe-mode: Ask, Which AI and the app's own AI command
   each say "AI is off in Safe Mode." and nothing opens.

Quill Weather:

5. Ctrl+Shift+G (Should I Go Out?): you hear "Getting weather for" your place,
   then the answer, and a window titled "Should I Go Out?" takes focus. With an
   active alert, the answer starts "Active alert, as the Weather Service wrote
   it:" and the alert's own words.
6. Ctrl+Shift+8, then "Do I need a coat at 5?" from Quick questions: the
   answer uses your place's name. Alt+A still presses Add Location.

Quill Converter:

7. With an empty queue, Ctrl+Shift+D says the queue is empty and opens
   nothing. With files queued, the device question takes focus; Escape cancels
   quietly; Enter with "iPhone" says "Reading the queued files", then the
   answer is spoken and its window is titled "Will This Play on My Device?".
8. Alt+A still presses Add Files. With Advanced Options shown, Broadcast polish
   is reached by Tab and no longer announces an access key.

Quill Media Player:

9. Ctrl+Alt+C in a book: "Summarizing this chapter. This may take a moment.",
   then the answer is spoken and a "Chapter Summary" window opens. Pressed
   again, it answers at once. With no AI chosen, Ctrl+Alt+R opens Choose Your
   AI and says once that no AI is in use.
10. Alt+A still plays or pauses. "Where am I?" no longer has an access key;
    Tab and Shift+F6 still reach it.

Quill Inkwell:

11. Ctrl+Shift+A on a .docx: the Yes/No question names the file, about how
    many words go and to which AI, and focus starts on No. Yes, then Suggest
    Abbreviations opens: every check box reads "not checked", Space checks it,
    and after OK you hear "Added" and the number.
12. Alt+N presses Quick Insert (it was Alt+I).

QuillBeacon:

13. Select a beacon with a picture and press Ctrl+F5: the first time on this
    AI you are asked where pictures go, No the default; then the description
    is spoken, its window takes focus, and "Add this to the beacon's note?"
    follows with No the default. Yes, then Ctrl+Z restores the note.
14. On the free AI, Ctrl+F5 offers the switch; answer No and "Read on This
    Computer" opens with the words OCR found, and nothing is sent.

Quill Radio and QUILL Cast, the picture consent:

15. In Quill Radio, show a video and press Ctrl+F5 on an AI that sees: the
    first time you hear "Pictures you ask about in QUILL Radio go to" and the
    company, Yes or No with No the default. No sends nothing; Yes describes it,
    and the next Ctrl+F5 does not ask again.
16. In QUILL Cast, press Ctrl+Alt+F5 on an AI that sees: the same question
    comes before the list of pictures, and No fetches nothing.

- [ ] All sixteen with NVDA.
- [ ] All sixteen with JAWS.
- [ ] Checks 1, 3, 5 and 11 with Narrator.

## My own key gains the AI Hub's providers, and one prompt list for the family, QUILL and QUILL Lite (codex.md decisions 18 and 20, 2026-11-01)

Use My Own AI Key (Alt+F2), in QUILL and then in QUILL Lite:

1. Open it and arrow through Provider: OpenAI, Google Gemini, Anthropic
   Claude, OpenRouter, Ollama Cloud, Custom OpenAI-compatible service, Ollama
   on this computer. Each is read once, with nothing else spoken over it.
2. Choose Ollama on this computer and Tab to About this: the first words read
   are "Runs on this computer. Nothing is sent." The API key box reads as
   unavailable and its label says none is needed; Server address reads
   http://localhost:11434 (or your saved address); the test button reads
   "Test the Connection" and Remove the Saved Key reads as unavailable.
3. With Ollama running, press Test the Connection: you hear "Ollama on this
   computer is running", the number of models and which one answered. With
   Ollama stopped, you hear that it did not answer, and nothing else.
4. Choose Anthropic Claude: the key box is available again and its label names
   Anthropic Claude; Server address reads as unavailable; Alt+V does nothing
   useful there and Alt+K lands in the key box.
5. Press OK on Ollama: you hear "AI help uses Ollama on this computer. Runs on
   this computer. Nothing is sent." Ctrl+4 then reads "My own key, Ollama on
   this computer" and its About line ends with "Runs on this computer. Nothing
   is sent."
6. With an Ollama model that reads pictures chosen, Ctrl+F5 asks once where
   pictures go and names "Ollama on this computer, and nowhere else"; with a
   text-only model it says pictures need a connection that can see.

The AI Hub (QUILL only):

7. Open AI > AI Hub. The Provider page reads "Provider in use" and the
   sentence naming the provider and model; the next Tab stop is "Open Use My
   Own AI Key", Alt+K. There is no provider list, key box or model box.
8. Press Open Use My Own AI Key: the Hub closes and Choose Your AI opens on the
   own key's row with Use My Own AI Key on top. Focus lands in that window,
   not back in the editor.
9. The On-Device page reads as one paragraph with no address box. The
   Advanced page has no Reset AI Settings button.

One prompt list:

10. On a profile with prompts in QUILL Lite's own prompts.json, start QUILL
    Lite: nothing is spoken about the move. Ctrl+7 lists those prompts, and a
    name QUILL already had with different words reads "(from QUILL Lite)".
11. Start QUILL afterwards: Ctrl+7 lists the same prompts. Quit and start
    again: nothing is added twice.

- [ ] All eleven with NVDA.
- [ ] All eleven with JAWS.

## Agent tasks across the family, Propose Alt Text and Tell Me When This Changes (codex.md Phase 4c, 2026-11-01)

Set up GitHub Copilot (or Codex) in Choose Your AI in each app first. Keyboard only.

QUILL and QUILL Lite, Propose Alt Text:

1. Open a Markdown file with two pictures, one with alt text and one without,
   saved beside it. On the free AI, AI > Propose Alt Text reads "(needs
   Copilot or Codex)" and pressing it offers to switch; say No and nothing
   opens.
2. On Copilot, press it: the window title is Do a Document Task, focus lands
   in Instruction and the reader says the filled-in request. Nothing is
   spoken by QUILL itself.
3. Press Enter. If the AI can see, Allow This Step? names the picture
   ("Send the picture ... from this document"); the first time on this AI a
   Yes/No about pictures follows, No the default.
4. Review AI Changes opens on one change only, the alt text for the picture
   without it. Accept: Ctrl+Z after the task removes exactly that change.
5. The closing summary is spoken once, for example "Done. 1 change applied:
   Set alt text for an image." The picture that already had alt text is
   untouched.

Each app's task (Quill Radio Find and Record and QUILL Cast Find and Follow on
Ctrl+F3; QUILL Transcribe Speakers, Sections and Summary on Ctrl+F3; QUILL
Studio Recording Pre-flight Check on Ctrl+3 and Narrate a Recording on
Ctrl+Shift+3; Quill Converter, Quill Media Player and Quill Inkwell on Ctrl+F3;
QuillBeacon Organize What I Saved on Ctrl+3):

6. On the free AI the row says "(needs Copilot or Codex)" and the key offers
   to switch, sending nothing. In Safe Mode the key says AI is off.
7. On Copilot the key opens the agent window with the app's own title; the
   reader says the title and the Instruction field, and the app says nothing.
   F1 on Instruction gives the app's own sentence.
8. Ask for something that changes data (follow a show, schedule a recording,
   tag an item, add abbreviations, write sections). Allow This Step? asks in
   one specific sentence; for a data change Review Proposed Change then shows
   the whole change as text, Enter applies and Escape does not. Say Don't
   allow once and confirm nothing changed.
9. The summary is spoken once and brailled; the conversation fills in
   silently and Shift+Tab reaches it. Stop ends a running task within a
   second; Close does the same.
10. Studio pre-flight: with the webcam microphone as default, the checklist
    names it. If the AI can see, the still is asked about first, naming what
    is captured.

Tell Me When This Changes (QUILL Studio, Quill Radio):

11. Studio: choose a window in Capture, press Ctrl+F9. Hear "Watching ... for
    changes." once. Change the words in that window: within a few seconds one
    sentence says what the words changed to, read on this computer.
12. Press Ctrl+F9 again: "Already watching". Press Ctrl+Shift+F9: "Stopped
    watching ...". Press it again: "Nothing was being watched."
13. Radio: with no video showing, Ctrl+F9 says there is no picture to watch.
    With a video stream showing, start a watch; hide the video and hear the
    watch stop with a reason.
14. On the free AI, Start Watching reads "(needs a connection that sees)" and
    offers to switch. In Safe Mode it is refused aloud. Declining the picture
    consent starts nothing.
15. Close the window while watching: nothing more is said or sent. AI Usage
    counts each question the watch asked.

- [ ] All fifteen with NVDA.
- [ ] All fifteen with JAWS.

## Describe a Folder, Describe Again and Save Described Copies, QUILL Studio (the Image Description Toolkit proposal, 2026-11-01)

Set up: a folder of about 12 pictures, some phone photos with dates and GPS,
one HEIC, one file renamed to .jpg that is not a picture. Studio on your
ChatGPT plan, then on your own OpenAI key, then on your own Claude key.

1. AI menu: Describe a Folder (Ctrl+Shift+F5), Stop Describing the Folder
   (Alt+Shift+F5), Describe Again (Ctrl+Alt+F5) and Save Described Copies
   (Ctrl+Alt+F6) are read with their keys. On the free AI, Describe a Folder
   and Describe Again add "(needs a connection that sees)" and offer to
   switch; Stop and Save Described Copies do not.
2. Ctrl+Shift+F5: the window opens on Folder of pictures. Tab reaches Browse,
   Include the pictures in subfolders, Prompt style (Accessibility chosen),
   the photo details check box (checked), the GPS check box (not checked),
   At most this many pictures in one run (25 on the plan), Continue and
   Cancel, each read with its name and state. F1 on each says what it does.
   Unchecking photo details disables and clears the GPS check box.
3. Continue: hear "Counting the pictures." then one Yes/No question naming
   the count and "OpenAI on your ChatGPT plan", No the default. No sends
   nothing and says nothing more.
4. Yes: hear "Describing 11 pictures. Press Alt+Shift+F5 to stop." then a
   count now and then, never once per picture. At the end: the count, the
   unreadable file by name, and QUILL opens on the document; heading
   navigation moves picture to picture.
5. Run the same folder again: the question says how many are described
   already, and only new pictures are sent. Add one picture and confirm only
   it goes.
6. Start a run and press Alt+Shift+F5 during it: "Stopping after the picture
   being described." then "Stopped. Described ..." and QUILL does not open.
   Alt+Shift+F5 with nothing running: "No folder is being described."
7. With the GPS box checked, the question adds "and the place it was taken".
8. Ctrl+F5 on a picture, then Ctrl+Alt+F5: the Describe again list starts
   with "The picture you described last". Choose Technical; the new
   description is spoken and the result window holds both, newest first,
   each labelled. Ctrl+Alt+F5 again with Technical: "Nothing was sent".
9. Ctrl+Alt+F5 on the folder with Concise: the count question comes first;
   the document lists Description 1 and Description 2 under each picture.
10. Ctrl+Alt+F6: choose the described folder, then the same folder again:
    a message says the copies need a different folder. Choose another: hear
    "Saved N described copies in ...", with WebP or HEIC pictures named as
    left out. In Explorer's Details for a copied JPEG, Comments holds the
    description; the original has none.
11. On an OpenAI key and then a Claude key, Describe a Picture and Describe a
    Folder work; the first picture asks the picture question naming OpenAI,
    then Anthropic.
12. Safe Mode refuses Describe a Folder and Describe Again aloud. Everything
    spoken is also brailled.

- [ ] All twelve with NVDA.
- [ ] All twelve with JAWS.
