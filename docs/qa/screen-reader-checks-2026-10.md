# Checks to Try With Your Screen Reader, October 2026

These are the hands-on checks for everything built in late September and early
October 2026 across QUILL Cast, Quill Radio, QUILL Lite and QUILL. There are
272 of them. Each one says where to go, what to press and what you should
hear. Check a box only after you have tried it yourself with a screen reader;
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
  Alt+Shift+2 the one before, through Alt+Shift+9; Alt+Shift+0 opens Recent
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
