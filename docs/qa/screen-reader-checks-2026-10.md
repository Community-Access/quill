# Checks to Try With Your Screen Reader, October 2026

These are the hands-on checks for everything built in late September and early
October 2026 across QUILL Cast, Quill Radio, QUILL Lite and QUILL. There are
149 of them. Each one says where to go, what to press and what you should
hear. Tick a box only after you have tried it yourself with a screen reader;
passing automated tests do not count.

Try them with NVDA, JAWS and Narrator where you can. When something is wrong,
write down the check, the screen reader and its version, and exactly what you
heard. Never put document text, passwords or keys in a report.

This list used to live in the working file qc.md, which was retired on
2026-10-03 once all its code work was done. The app-by-app sign-off sheets in
this folder are still the place to start for a release; this page covers what
is new since they were written.

## Still to do in the code

- **QUILL's own documentation** -- its user guide, release notes, tutorials and
  the QUILL pages of the website -- gets the same people-first, beginner-first
  rewrite that QUILL Cast, Quill Radio, QUILL Lite and the site received on
  2026-10-03. Jeff asked for QUILL to come last.

This section records user-experience changes implemented in source, not a
release announcement. Test the current source build; older installed builds
may not contain these changes. All manual checks below are pending. Automated
test passes do not mean speech, braille, native Alt+Tab, or every app was
manually verified. Do not tick a checkbox until a human completes that check.

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
- [ ] Radio: a recording that finishes is in Activity, "Recording saved: ...",
  with Open Folder; one that captured nothing is listed as failed with its
  reason.
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
