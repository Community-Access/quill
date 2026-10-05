# QUILL Lite changelog

## 1.2.0 -- 2026-10-03

### Dictating in Spanish (2026-10-04)

- **Dictation language** in Dictation Settings (**Alt+Shift+F6**): English or
  Spanish. In Spanish your words come out in Spanish, accents and all, using
  Whisper's multilingual model, which comes with QUILL Lite; Windows speech
  recognition uses a Spanish recogniser when Windows has one.
- Commands stay in English for now. Spanish punctuation words ("coma",
  "punto", "punto y aparte" and the rest) work when automatic punctuation
  is off. The wake and stop phrases become "Quill dicta" and "deja de
  dictar".
- Shared with QUILL, through the same code.

### Open from the clipboard, a link or a drop, honest encodings, and a careful Save (2026-10-04)

More ideas from **PlanCake**, by **Andre of Oire Software**. Thank you, Andre.
All of it is shared with QUILL, on QUILL's keys.

- **Open from Clipboard** (**Ctrl+Alt+Shift+Enter**, **File** menu): files
  copied in File Explorer, a file path copied as text, or a web link.
- **Open from URL...** (**Alt+F, F**), new in QUILL Lite: asks before
  downloading, naming the website and the size, shows progress with a Cancel
  button, and opens the download as a new unsaved document.
- **Drag and drop to open:** drop files on the window or the editor. Dropped
  text is still inserted.
- **A remembered Reload never throws away unsaved edits.** "Do not ask me
  again" with Reload was an answer about an untouched document; with unsaved
  edits QUILL Lite now asks the normal question instead. Shared with QUILL.
- **No more lost bytes in older files.** A file that was not UTF-8 used to be
  read as Windows-1252 with replacement characters, which the next save wrote
  over five byte values. Now every byte is read and saved back, and QUILL Lite
  says once as it opens when a file is not UTF-8.
- **Reopen with Encoding...** in the File Encoding and Line Endings window
  reads the file again as a code page you choose.
- **Save checks first:** if another program changed the file since you opened
  or last saved it, Save asks: Save As, Reload from Disk, Overwrite or Cancel.
- **Watching for outside changes as you work,** the way QUILL does and from
  QUILL's code. Each open document notices when another program changes or
  deletes its file. An unchanged document can reload by itself, keeping the
  cursor's line, and says once "Reloaded plan.md: changed by another program."
  Otherwise QUILL Lite asks once per change: Keep Mine (Enter and Escape),
  Reload from Disk or Save As..., with a "Do not ask me again" box per kind of
  file. A deleted file is said once and the document is marked not saved.
- Four new settings in Preferences, under **When another program changes the
  file**, with QUILL's names: **Watch the open file for external changes**,
  **Reload automatically when you have no unsaved edits**, **Ask before
  discarding unsaved edits on a conflict** and **External-change debounce
  (milliseconds)**, plus **Forget remembered file-change answers**.
- The user guide no longer says the Heading Organizer cannot work in rich text.
  It has since 1.2.0.

### Inline notes, task lists and a page to share (2026-10-04)

The ideas here come from **PlanCake**, a small Windows app by **Andre of Oire
Software** for reviewing the plans AI assistants write. Thank you, Andre. All
of it is QUILL's own code, shared, on QUILL's keys.

- **Inline notes**, on **Tools > Inline Notes**: **Add Inline Note...**
  (**Alt+Shift+I**), **Next Inline Note** (**Alt+Shift+J**), **Previous Inline
  Note** (**Alt+Shift+K**), **Speak Inline Note** (**Alt+Shift+H**; twice to edit),
  **Delete Inline Note...** (**Alt+Shift+Delete**) and **List Inline Notes...**
  (**Alt+Shift+Enter**), which shows every note and can go to, edit, delete,
  remove all, copy all and export them as Markdown or JSON.
- **Notes in the file:** in Markdown and HTML, a note can be written into the
  document as a hidden comment that anyone reading the file can see, instead of
  staying private. Turn it on per note, or for every new note with
  **Write new inline notes into the file** in Preferences.
- **Notes from the command line:** `QuillLite.exe --notes list|check|clear
  FILE`.
- **Snippets moved** from **Alt+Shift+I** to **Ctrl+Alt+Shift+Home**, so the
  note keys are the same as QUILL's. QUILL answers the new key too.
- **Toggle Task Done** (**Ctrl+Alt+Enter**, **Format** menu) ticks `- [ ]`
  tasks and says how many in the list are done.
- **File > Export as HTML...** (**Ctrl+Alt+Shift+End**) saves a copy as one web
  page you can share, with task lists as check boxes.

### Portable copies start from a folder with a space in its name (2026-10-04)

- A portable copy unpacked to a folder whose name has a space in it said it did
  not start. The QuillVille launcher passed its own path to Python unquoted,
  so Python read it as two words; the same mistake split a document opened
  from File Explorer out of such a folder. Every release before 1.2 had it
  (`quill/native/launcher/cmdline.c`).

### Recent Documents: the whole list on Alt+Shift+0 (2026-10-04)

- **File > Recent Documents...** (**Alt+Shift+0**) lists every document you
  opened recently. Enter opens one; you can also pin a document so it stays at
  the top, remove one from the list, open its folder, clear everything that is
  not pinned (it asks first, and No is the default), and choose how many to
  remember (1 to 50) and whether deleted files drop off at startup.
- **File > Open Recent** puts pinned documents first. A file on a USB drive or a
  network share stays on it while the drive is unplugged; only a file deleted
  from this computer's own drives is left out.
- QUILL has the same window on the same key. The two keep separate lists.

### Remove Quote Marks has a key that works (2026-10-03)

- **Remove Quote Marks** is now **Alt+Shift+.** (Alt, Shift and the period).
  Its old key, Ctrl+Alt+Shift+Q, is the key that shows and hides QUILL from
  anywhere in Windows, so whenever QUILL was running it got the keystroke and
  QUILL Lite never did. QUILL moved its Unquote Lines to the same new key.

### Release channels: safe ways back, background downloads, and updates that undo themselves (2026-10-03)

- **Coming back to Stable can now go straight back** when Stable can read
  everything QUILL Lite has saved. When it can't, the window says so and offers to
  wait for Stable or to put back the copy saved when you joined Beta (a copy of
  how things are now is saved first).
- **Beta and Dev download updates in the background** and never install
  without asking; they wait on a metered connection, during Quiet Hours and
  while Quill Radio records.
- **Beta and Dev get their own copy of the shared engine** (about 335 MB, gone
  when the last app returns to Stable), so moving one app never touches the
  others. The "move together" rule is lifted for installs that have it.
- **A failed update undoes itself** and says so the next time QUILL Lite starts;
  Update History records it.
- Updates come from a signed list of versions, with downloads checked against
  it and resumed when interrupted.

### Release channels: Stable, Beta and Dev (2026-10-03)

- **Help > Release Channel...** (no key), and a Change release channel...
  button in Settings, open the family's shared window (`quill/ui/updates/`). The
  choices only explain as you arrow; Beta and Dev ask first in plain words and
  need "I understand" ticked; a zip of QUILL Lite's settings, keys and recent
  files is saved to `channel-snapshots` before anything moves. QUILL Lite shares
  the QuillVille engine with Quill Radio and QUILL Cast, so for now they join
  Beta together. Coming back never installs an older version; QUILL Lite waits
  for Stable to catch up and says so.
- Check for Updates honours the channel and picks the newest release by version,
  not by GitHub's list order (it used to take the first stable one listed), and
  asks for 100 releases a page. Each launch records the data formats QUILL Lite
  writes in `data-format-ledger.json` (recording only).
- No chord, the same as QUILL, Quill Radio and QUILL Cast: Alt+Shift+F4 was
  tried and dropped, because in a dialog Windows reads it as Alt+F4 and closes
  the window (family rules 4 and 9; `KEYLESS_WITH_REASON` in
  `tests/unit/core/lite/test_lite_commands.py`, `cmd_release_channel` ->
  `help.release_channel` in the parity table).

### QUILL Lite as your Windows text editor (2026-10-03)

- **The installer always registers QUILL Lite as a capable text editor and
  takes nothing over.** A `QuillLite.Document` ProgID (DefaultIcon,
  `shell\open\command` = `"{app}\QuillLite.exe" "%1"`), a `QuillLite.Document`
  value in `OpenWithProgids` for .txt .text .log .md .markdown .rtf .html .htm
  .csv, `Applications\QuillLite.exe` (FriendlyAppName, SupportedTypes), and
  `Software\QuillLite\Capabilities` + `RegisteredApplications`, so QUILL Lite
  is listed in Settings > Apps > Default apps. HKA: HKCU for a per-user
  install, HKLM for an administrator one; every key and value goes on
  uninstall, and a type's own key never does. `ChangesAssociations=yes`. The
  optional "assoc" component, Custom installs only and drawn as a check list
  a screen reader reads as unchecked, is gone. No `UserChoice` key is ever
  written.
- **Make QUILL Lite My Text Editor...**, a button in Preferences under Windows
  and your files (no menu row and no key, in either editor), explains
  what Windows lets an app do and what the user chooses, writes the same keys
  for the current user pointing at the running `QuillLite.exe` (so a portable
  copy works), and opens Default apps on QUILL Lite's own page
  (`ms-settings:defaultapps?registeredAppUser=QUILL%20Lite` on Windows 11,
  the general page on Windows 10). When an administrator install already
  registered this copy for everyone, it writes nothing and opens the
  `registeredAppMachine` page instead, so no uninstaller-orphaned copy is
  left in the profile.
- **Open QUILL Lite instead of Notepad**, a checkbox beside it, off by
  default. It sets `Debugger` = `"<launcher>" --notepad`
  under `Image File Execution Options\notepad.exe` (HKLM, every user), on the
  parent key and on each Windows 11 `UseFilter` subkey whose `FilterFullPath`
  is a Notepad, through one `cmd.exe /c reg.exe ...` run with the `runas`
  verb after a confirmation that names the scope, the administrator prompt,
  and the undo. Turning it off removes only QUILL Lite's own values; another
  program's replacement is named before it is replaced and never removed. The
  checkbox is read back from HKLM each time Preferences opens. On Windows
  11 it then explains the Notepad app execution alias and offers
  `ms-settings:advanced-apps`. The uninstaller removes any value naming its
  own `QuillLite.exe`, asking for approval when it is not elevated.
- **`--notepad` on the command line**: Windows' own Notepad path is dropped,
  Notepad's switches (/A /W /P /PT) are dropped, an unquoted path with spaces
  is joined back into one file, and no file means a new plain text document.
  /P opens the file rather than printing it. The handover to a running copy
  is unchanged.
- Code, shared with QUILL, which has the same two settings: `quill/core/windows_editor.py`
  (what to write, wx- and registry-free, one profile per app),
  `quill/platform/windows/editor_registration.py` (winreg, `ShellExecuteEx`
  runas, Settings), `quill/ui/text_editor_commands.py` (the flows) and
  `quill/ui/text_editor_prefs.py` (the Preferences group, the only door).
  QUILL Lite binds its profile in `quill/core/lite/windows_editor.py` and
  `quill/apps/lite_window_text_editor.py`. Tests:
  `tests/unit/core/lite/test_lite_windows_editor.py`,
  `tests/unit/apps/test_lite_text_editor_commands.py`,
  `tests/unit/scripts/test_quilllite_text_editor_installer.py`.

### Each app keeps its own ChatGPT sign-in (2026-10-02)

- The family's apps share one data folder, and until now one ChatGPT record:
  signing in to a second app overwrote the first app's registration while
  each kept its own token, so the first believed it was signed in and could
  not refresh. Each app now keeps its own record under its own name
  (`ai/chatgpt-quill-lite.json`; the old shared file is read until QUILL
  Lite writes its own), signing out of one leaves the others signed in, and
  Use My ChatGPT Subscription says when another app is already signed in on
  this computer -- the browser then is too, and Continue is one Allow.

### Your own key can be a Google Gemini key (X-07)

- **Use My Own AI Key (Alt+F2)** -- the row was Use My Own OpenAI Key -- opens
  on a **Provider** list: OpenAI, or Google Gemini. Everything under it
  follows the choice: where the text goes, which key, that account's own
  models with that company's prices, Test the Key against that company. The
  choice is explicit and saved (`ai_own_key_provider`, the same field as
  QUILL's); nothing is inferred from a saved key or a model name, and a key
  for the other provider is reported, never used. Both keys may be saved.
  With a Gemini key, Ask About an Image works too, because Gemini reads
  pictures. Every AI help command, the dictionary and Tidy Dictated Text run
  on the chosen key (`quill/core/ai/own_key.py`, `own_key_models.py`,
  `quill/ui/hosted_ai_own_key.py`, `hosted_ai_own_key_route.py`;
  `tests/unit/core/ai/test_own_key_gemini.py` drives a Gemini-shaped
  loopback server with a synthetic key).

### A thesaurus that finds the word you are on, Look Up, and an AI dictionary (2026-10-02)

- **Tools > Thesaurus... (Shift+F7)**, QUILL's two-pane picker and QUILL's
  data, which ships inside QUILL Lite. It looks up the word you are *on*:
  "running" reaches "run", "happier" reaches "happy", irregular verbs are
  known, and every replacement comes back in the form the sentence needs,
  with the original's capitals ("sprinting" for "running", "More glad" for
  "Happier"). QUILL's own Thesaurus now does the same, from the same code
  (`quill/core/word_lookup.py`, `quill/ui/word_tools_commands.py`).
- **Two submenus on any word in the context menu.** *Thesaurus for "word"*:
  the best replacements one keystroke away, each further sense as a submenu,
  Opposites, Say Word Summary and More in Thesaurus. *Dictionary for
  "word"*: Look Up, then the AI dictionary's twelve questions when AI help is
  on, or one row that says what it needs. The same two submenus in QUILL
  (`quill/apps/lite_window_context_menu.py`, `quill/ui/main_frame.py`).
- **Say Word Summary (Ctrl+Alt+Shift+[)** speaks what the thesaurus knows --
  the headword, the meanings per part of speech, the first replacements and
  the opposites -- without opening anything.
- **Tools > Look Up Word... (Alt+F10)**: QUILL's Look Up window, the
  dictionary without AI, shared by both editors. Offline it is the thesaurus;
  with **Use online sources** ticked -- off until you tick it, remembered as
  `dictionary_online_lookups` -- the word alone goes to the Free Dictionary,
  Datamuse and Wikipedia for definitions, more words and a summary, arriving
  in the background. Words you can use replace the word on Enter; Add to
  Dictionary teaches it (`quill/ui/lookup_window.py`, `quill/core/lexical.py`).
  In QUILL this window had been reachable only when the thesaurus data was
  missing, and went online whenever the dictionary feature was on; now it is
  on the Tools > Writing menu and asks first.
- **Tools > Dictionary**, the AI dictionary: Define in Context, Synonyms That
  Fit, Simpler, More Formal and More Vivid Word, Opposites, Is This the Right
  Word?, Use It in a Sentence, Where It Comes From, How to Say It, Rhymes, the
  Word Explorer (everything at once) and Find the Word For (the reverse
  dictionary). Each sends the word and its sentence, never the document, and
  answers in prose for listening plus choices that each say why; Use This
  Word replaces the word (or inserts, for Find the Word For) as one undo
  step, and only while the word is still where it was. On your own key
  (OpenAI or Google Gemini) or ChatGPT subscription only -- never the free
  allowance -- and the same
  rows, keys and window in QUILL's AI menu (`quill/core/ai/word_tools.py`,
  `quill/ui/word_tools_window.py`, `quill/ui/main_frame_hosted_ai.py`).
- **Tools > Spelling > Dictionary Status... (Alt+Shift+;)**, QUILL's row: the
  word counts and file paths of your dictionaries, and whether the thesaurus
  data is present (`quill/apps/lite_window_words.py`).
- A new Customize Features area, **Dictionary and thesaurus**, on by default
  and off in the WordPad and Notepad profiles; the AI rows switch with AI
  help. The profiles' counts are 17, 21, 5 and 2 of 21.

### Activity, Repeat Last Result, and saves that tell the truth (F-01, F-02, F-10)

- **Help > Activity... (Shift+F9)** lists every result this session, newest
  first, each with what you can do about it: Retry, Open Folder, Copy
  Details, Clear List. **Help > Repeat Last Result (F9)** says the newest
  result that mattered again. The same two keys and the same window in QUILL,
  Quill Radio and QUILL Cast; every document window shares one list, and
  work still running is listed beside what finished
  (`quill/core/activity.py`, `quill/ui/activity_window.py`,
  `quill/apps/lite_window_activity.py`).
- **A settings save that fails is said once, with a way back.** Every settings
  and history writer in the family -- QUILL Lite's and QUILL's settings, Quill
  Radio's and QUILL Cast's history, the podcast library -- goes through one
  guard that reports how the write went. A failure reaches Activity with the
  reason (disk full, denied, read only, missing folder), a Retry that writes
  the same thing again and an Open Folder; the same file's failure is not
  repeated for a minute, and the save that later works is said too
  (`quill/core/persistence_outcome.py`, `quill/ui/persistence_reporting.py`).
- **Background work that finishes after its window closed is not lost.** It
  used to be dropped without trace. It is now a review row in Activity, never
  spoken (`quill/ui/surface_lifetime.py`).

### Large and networked files open without freezing the window (F-05)

- **Opening read the whole file on the UI thread.** A large file, a slow
  network share or a damaged RTF made the window stop responding with nothing
  said. Opening is now prepare (read, decode or safety-scan, on a worker) then
  commit (into the editor, on the UI thread, only if the window still wants
  it). Files of 1 MiB or more and UNC paths take that route; others open as
  before. Busy is said once, the empty document is read-only until the text
  arrives, closing the window cancels, and a failed read offers Try Again
  (`quill/core/lite/open_prepare.py`, `quill/apps/lite_window_open.py`,
  `tests/unit/apps/test_lite_background_open.py`).
- **A background open is listed in Activity.** While it runs it is an
  in-progress row; afterwards it is kept as Opened, or Could not open with the
  reason, so a slow file that finished while you were elsewhere can be checked
  (`quill/apps/lite_window_open.py`, qc.md F-10).

### Find a setting, a focus repair with limits, and a tidier close (2026-09-30)

- **Preferences has a Find a setting box.** It searches each setting's name,
  what the screen reader calls it and its help text; Down reaches Matching
  settings and Enter moves focus to the control. Ctrl+F returns to the box,
  Escape clears it first, and searching never changes or saves a setting
  (`quill/ui/preferences_search.py`, shared with every app's Preferences:
  Quill Radio and QUILL Cast have the same box).
- **Alt+Tab back into QUILL Lite puts focus in the document.** The activation
  repair runs once with one bounded follow-up check; menus, real fields such
  as Find, hidden windows, deactivation and shutdown are left alone, and a
  stale callback from an earlier activation does nothing.
- **A settings save that fails is reported, not discarded.** Your choices stay
  active for the session, the warning stays reviewable in the status bar's
  Message cell, reopening Preferences retries the save, and Preferences no
  longer says "saved" when it was not. Diagnostics carry no raw file-system
  errors or paths.
- **Closing is tidier.** The inbox that receives documents from a second
  launch stops before the documents are destroyed; a cancelled close keeps it
  running; documents sent while QUILL Lite closes are opened next time; and a
  deferred update check never starts once closing has begun.

### A focus repair that does not take leaves a trace (F-04)

- When the Alt+Tab focus repair is overruled, QUILL Lite now counts it and
  writes one line to its log: `QUILL-LITE-FOCUS-MISS`, the kind of control that
  holds focus, and how many times this session -- no titles, labels or text.
  It says nothing aloud. This is what a support bundle needs to tell an
  intermittent focus report from a one-off (`quill/apps/lite_shell.py`).

### Two instances stop undoing each other's preferences (F-11)

- **Last closed used to win the whole file.** With `--new-instance`, both
  processes wrote their whole copy of the settings, so whichever saved last
  reverted every preference the other had changed. A save is now a three-way
  merge per field against the file as it is at that moment: fields this
  instance changed are written; the rest keep what is on disk. The running
  instance is never changed under the listener; the other's choices apply at
  its next launch (`quill/core/lite/settings_merge.py`,
  `quill/apps/lite_settings_persistence.py`,
  `tests/unit/core/lite/test_lite_settings_merge.py`).

### Exit without a traceback

- **A crash on the way out.** Closing QUILL Lite could end with
  `RuntimeError: wrapped C/C++ object of type Panel has been deleted` from
  the status bar's refresh. The close path stopped the bar's coalescing
  timer and then destroyed the window, and the teardown in between -- the
  editor's own last text and focus events, the settings flush -- marked the
  bar stale again, which re-armed the timer on a window about to be gone.
  The stop is now one-way: once the window is closing, marking the bar
  stale arms nothing, and a refresh that somehow reaches a destroyed panel
  returns instead of raising (`quill/apps/lite_window_status.py`,
  `tests/unit/apps/test_lite_status_lifetime.py`).

## 1.1.2 -- 2026-09-30

### Install and restart now installs, and restarts

- **The one-click update ran nothing.** Choosing *Install and restart now*
  closed QUILL Lite and then nothing happened: no installer, no restart, and no
  log to say why. The app's launcher runs it inside a Windows job that ends
  every process the app started when the app closes -- a safety net so a
  crashed launcher never leaves a hidden process behind -- and the small
  helper that waits for the app to close and then runs setup was one of those
  processes. It was ended while it waited. The helper now leaves that job
  before it starts: launchers from this release allow exactly that, and under
  a launcher already installed it is started by Windows' own management
  service instead, outside any job. Tested against real Windows job objects of
  both kinds, and against the old code, which loses its helper every time
  (`quill/core/self_update.py`, `quill/native/launcher/launcher.c`).
- **A failed update leaves a log.** The helper writes to an `updates` folder
  that did not always exist, so a failure left no trace; the folder is now made
  first.
- **Updating from 1.1.1 or earlier:** those versions still carry the old
  helper, so this one update is by hand once. Choose *Open folder* in the
  update window and run `QuillLite-Setup-Shared-1.1.2.exe`, or download it from
  quillforall.org. From 1.1.2 on, *Install and restart now* works.

## 1.1.1 -- 2026-09-30

### The version number that ran ahead of the release

- **Why 1.1.1 exists.** It is 1.1.0 with one thing changed: the number. QUILL
  Lite's version was set to 1.1.0 in the source on September 25, four days
  before 1.1.0 shipped, and Quill Radio 3.0.3 and 3.0.4 were built from that
  source in between. The shared QuillVille Runtime those Radio installers put
  on a computer carries every app's code, QUILL Lite's included -- so on any
  computer with Radio 3.0.3 or 3.0.4, Help > About in QUILL Lite already said
  1.1.0, and Check for Updates, comparing 1.1.0 with 1.1.0, said "you are up to
  date" and never offered the real release with the ChatGPT subscription,
  pictures and dictation. 1.1.1 is newer than any number a runtime could have
  claimed, so every copy is offered it.
- **The version no longer comes from the shared runtime.** The installer now
  writes the version it installed into QUILL Lite's own folder
  (`quill-app-version.ini`), and Check for Updates and Help > About read that,
  not the constant inside whatever runtime happens to be on the computer. A
  sibling app's newer runtime can no longer make QUILL Lite look up to date.
  When the runtime's code is from a different release, About says both, for
  example "1.0.0 (running shared runtime code 1.1.0)", so support can see it
  (`quill/core/app_version.py`; Quill Radio reads its version the same way).
- **And the builds refuse to create the mismatch: GATE-SIBVER.** Every release
  build checks each app's source version against its newest published release
  before the runtime is built, and fails when an app is ahead of its release
  without being the app that build is releasing (`scripts/check_sibling_versions.py`,
  wired into every `build_release.ps1`). A version number changes in the
  release commit, and never before. Its first run caught the next one waiting:
  Quill Radio's source already said 3.1.0, unreleased, so it is held at 3.0.4
  until Radio's own release.
- If you are on 1.1.0 already, nothing else is different; 1.1.1 is the same
  QUILL Lite.

## 1.1.0 -- 2026-09-29

### Your ChatGPT subscription, pictures described, and web search (2026-09-29)

- **Use My ChatGPT Subscription** (Tools > AI, **Alt+F5**). If you already pay
  for ChatGPT, QUILL Lite runs every AI command on that plan: **Continue with
  ChatGPT** opens your browser on OpenAI's own sign-in page, you allow "QUILL
  Lite" to use your plan, and you come back signed in -- no key, no monthly
  allowance, no size limit, no per-request bill, nothing through QUILL's
  servers. QUILL Lite registers itself with OpenAI at sign-in (there is no
  secret in the build), signs in with PKCE, checks the ID token's issuer,
  audience, nonce and expiry, and keeps only the refresh token in Windows'
  credential store under its own name; the access token lives in memory and is
  renewed as needed. A sign-in is used ahead of a saved OpenAI key. **Sign Out**
  (two presses) asks OpenAI to revoke it and forgets it here; **Forget on This
  Computer** forgets it here only; neither button exists until you are signed
  in (`quill/core/ai/chatgpt_account.py`, `quill/ui/hosted_ai_chatgpt.py`).
- **The model is your plan's list.** Read from your account the moment you
  sign in, Luna 6 and GPT-6 first, the first one chosen for you, and saved as
  you arrow to another. **Refresh Models** reads it again.
- **Ask About an Image** (Tools > AI, **Ctrl+F5**). The first AI command that
  takes a file: choose a JPEG, PNG, WebP or GIF, type a question or none, and
  hear what the model sees -- a description written for a blind reader, with
  any text in the picture transcribed exactly. The file is checked and
  re-encoded before it is sent, so a mislabelled or damaged file is a sentence
  rather than a failed request. The answer opens in an **Image Description**
  window with Insert Below, Copy, and Ctrl+Z to take an insert back. With no
  sign-in it says so and opens the account window
  (`quill/ui/hosted_ai_image.py`, `quill/core/ai/chatgpt_client.py`).
- **Allow web search.** A checkbox in the account window, off by default. On,
  the model may search the web through OpenAI to answer a general question, a
  question about the document, or a conversation turn.
- **Tidy Dictated Text** (Tools > AI, **Ctrl+F3**). Dictation's AI: the
  selection, else the paragraph at the cursor, goes to the model with an
  instruction to correct misheard words, punctuation, capitalisation, fillers
  and false starts and change nothing else; the Tidied Dictation window offers
  Replace My Selection, and Ctrl+Z takes it back as one step. Runs on a ChatGPT
  plan or an own key only (the free service has no such template); with
  neither it opens the account window and says why
  (`quill/ui/hosted_ai_chatgpt_commands.py`, `INSTRUCTIONS["tidy_dictation"]`).
- **The same seventeen tools, the same words.** On the plan, requests carry the
  gateway's own instructions through OpenAI's Responses API (`store=false`,
  `stream=true`, as the plan requires), so a summary is the same summary
  whichever way it travels. Conversations go as real turns.
- **Usage and About follow the route.** Usage (Ctrl+Alt+Shift+F9) opens the
  account window on a plan, with **Open ChatGPT Usage** for the plan's own
  page; About names the account and the model.
- **Five error codes** with a next step each: `QUILL-AI-CHATGPT-SIGNIN`,
  `-SIGNED-OUT` (OpenAI no longer accepts the sign-in; it is forgotten locally
  and Continue with ChatGPT starts clean), `-LIMIT` (the plan's usage for now),
  `-UNAVAILABLE` and `-FAILED`.
- **QUILL has the same two rows on the same two keys**, in its AI menu, from the
  same shared module; and **Quill Radio** gains Ask QUILL Radio on the same
  sign-in, as its own agent. Each app appears as itself under Apps in ChatGPT's
  settings, and signing one out leaves the others connected.

### Coming back to QUILL Lite puts you back in your document (2026-09-29)

- **Alt+Tab back into QUILL Lite lands in the edit box.** A reader wrote that after Alt+Tabbing to another program and back, focus did not always return to the document, and that it was hard to reproduce -- pressing Ctrl+Tab once seemed to cure it. Both halves have the same cause. QUILL Lite keeps its documents inside one window, and Alt+Tab can only see that outer window; Windows then puts focus back wherever it was last inside it, which after an Alt+Tab can be the window frame itself rather than the edit box, and nothing moved it on. Ctrl+Tab and Ctrl+F6 set focus on the document explicitly, so switching documents once corrected what Windows remembered and the problem stopped for the rest of the session. Coming back to QUILL Lite now puts focus in the document. A box you had moved to on purpose keeps it -- Find, a field you tabbed to, a window that opened as QUILL Lite came forward -- because taking focus away from those would be the worse bug (`quill/apps/lite_shell.py`).

### Dictation, made reliable, and taught your words in a window (2026-09-28)

Nine items from the dictation plan, all shared with QUILL's Live Dictation.

- **Escape cancels the phrase being heard.** While the status cell says
  "hearing you", Escape throws the phrase away, nothing is written, and you
  hear "Cancelled". Ctrl+F11 still stops and keeps what you said; when nothing
  is being heard, Escape is untouched. The engine's half-finished audio is
  discarded too, so a phrase it finalises afterwards is not written late.
- **The microphone watchdog.** A device that stops delivering sound, or delivers
  digital silence for three seconds, pauses dictation: "The microphone stopped.
  Dictation is paused and will resume when it comes back." Dictation stays on,
  the status cell says "paused, microphone lost", and the device is tried every
  two seconds; "Microphone back. Listening." resumes it. A quiet room never
  counts as silence.
- **One Ctrl+Z per phrase.** A phrase that replaced a selection was two undo
  steps (remove, then write). Every phrase now goes in through the same
  single-undo path the AI inserts and paste use, so "scratch that" and Ctrl+Z
  always agree.
- **Read-only documents refuse before the microphone opens**, in the plan's
  words: "This document is read-only, so dictation cannot write here."
- **The engine heals itself.** The first time the speech engine stops
  answering, it is restarted silently; a decode that raises is retried once on
  a freshly loaded engine. The second failure is reported by name with a next
  step: "Moonshine stopped working. Try Whisper in Dictation Settings."
- **One dictation session at a time.** Ctrl+F11 in a second document while
  dictation runs in the first moves it there -- "Dictation moved to Letter.txt"
  -- instead of two sessions fighting for one microphone.
- **Dictate into any text box.** Ctrl+F11 in Find, either Replace box, or the
  AI pad's question dictates there; a paragraph break is a space in a one-line
  box, and nothing there gets a closing full stop.
- **Recent Phrases...** (Shift+F11): the last twenty phrases this session,
  newest first, with Insert Again (one undo step) and Copy. Memory only.
- **My Words and Phrases...** (Alt+Shift+F10, and the button in Dictation
  Settings that used to open the file): a window with Add Word, Add Phrase,
  Add Correction, Edit and Remove. **Corrections** are new: what the engine
  keeps hearing wrong and what to write instead, applied after recognition on
  every engine. Each change is saved at once and said back. Open the File is
  still there for anyone who prefers `dictation.md`, which is unchanged in
  shape apart from its new Corrections heading.
- Also fixed on the way: the explanatory sentences in the starter
  `dictation.md` were being read as vocabulary words.

### Launcher (2026-09-28)

- **When QUILL Lite cannot start, it says so.** `QuillLite.exe` starts the
  app's Python engine and used to discard the result: the engine has no
  console, so an error at start-up went nowhere, and a file Windows refused to
  load ended it before any Python ran. Now the launcher keeps a launch log of
  everything the engine reports (`data\logs\launch.log` beside a portable
  copy; `%APPDATA%\Quill\logs\QuillLite-launch.log` for an installed one) and,
  when the engine exits with an error, opens one plain message a screen reader
  reads on its own: "QUILL Lite did not start", the reason in words, where the
  log is, and the support address. A missing DLL, a damaged or 32-bit file and
  "access denied" each get their own words. Opening `QuillLite.exe` from inside
  the zip, before extracting it, is recognised and explained. Shared with every
  QuillVille app (`quill/native/launcher/launch_report.c`); first shipped in
  Quill Radio 3.0.4 and Quill Converter 1.0.0.

### Updates (2026-09-28)

- **Install when I close.** When an update has downloaded, the window offers
  it beside **Install and restart now**: keep working, and the update is
  installed the next time you close QUILL Lite; the next time you open it, it
  is the new version.
- **A portable copy updates itself.** The portable updater refused ("not a
  packaged build") because the running Python is the bundle's `pythonw.exe`;
  it now updates the folder `QuillLite.exe` is in, keeping `data`, and restarts
  through `QuillLite.exe`.
- **The Tutorials book opens** from a packaged copy again: it looked for its
  documents beside the shared engine rather than beside `QuillLite.exe`.

### Installer (2026-09-26)

- **The installer's checkboxes are real Windows checkboxes.** Create a desktop
  icon and Launch QUILL Lite now tell a screen reader whether they are checked;
  the old list announced every box as not checked. Both still start unchecked.

### Support (2026-09-26)

- **No GitHub token, in the app or the build.** Every message from QUILL Lite
  already went to support@community-access.org through your own mail program;
  now the build stops generating and embedding the bundled GitHub "feedback
  token" it never needed, and a release no longer fails without one
  (`-TokenFile` and `-SkipToken` are gone from `scripts/build_release.ps1`).
- **Get Help from Support is email, and only email.** The feedback-hub
  dialog it used to try first is gone, and with it any way for a support
  message to end up as a public issue.
- **The email field says what is true.** Its F1 help used to warn that leaving
  it empty meant nobody could answer you. The message goes from your own mail
  account, so support can answer that; the field is for an answer somewhere
  else.
- The user guide's **Getting help** section is now a full step-by-step
  walkthrough: every field and its key, what happens after Send, what to do
  with no mail program, and what is and is not included.

### AI help

- **Ten writing tools** in the AI pad (**Ctrl+Alt+G**), which goes from seven
  choices to seventeen: **Shorten**, **Simplify**, **Make more formal**, **Make
  friendlier**, **Turn into a list**, **Find action items**, **Suggest
  headings**, **Continue writing**, **Write an email reply** and **Translate**
  (a **Translate into** list of twenty languages appears when it is chosen).
  Each works on the same passage Summarize does and is one request of the same
  size; each has a monthly share of 60 and can be switched off on the service.
  The table lives in `quill/core/ai/writing_tools.py`, shared with QUILL.
- **Have a conversation.** A seventh choice in the AI pad (**Ctrl+Alt+G**)
  opens the **AI Conversation** window: talk back and forth, and each reply
  remembers what was said before. **Follow Up** in every answer window carries
  on from that answer (a follow-up to a question about the document keeps
  sending the same passages). Focus stays in the message box; each reply is
  read aloud as it arrives. On the free service every message is one request,
  conversations have a monthly share of 40, and the conversation so far is sent
  only as far as the ordinary size limit allows -- so a turn never costs more
  than any other request, and the window says when a long conversation starts
  forgetting its beginning. With your own OpenAI key the whole conversation
  goes, with no limit.
- **Ask a general question.** A sixth choice in the AI pad (**Ctrl+Alt+G**):
  type any question and get an answer, with nothing from your document sent.
  One question, one answer -- not a conversation -- so it fits the free
  allowance. Its answer may run to about 750 words.
- **No limits with your own OpenAI key, and warnings instead.** Nothing is
  refused for size, the answer is not capped, and a question about the document
  sends the whole document rather than three passages. Before you send, the pad
  says how many words are going, roughly what they cost with your chosen model,
  and when the text is more than the free service or the model would take.

### Dictation

- **Dictation** (**Tools > Dictation**, **Ctrl+F11**). Press it, talk, and
  pause: each phrase is written at the cursor, a soft tone confirms it went in,
  and the words are read back so you can hear whether they are what you said.
  It keeps listening until you press Ctrl+F11 again or say "stop dictation".
  Nothing to download, nothing leaves the computer, and no recording is kept.
- **Punctuation by itself.** The built-in engines add full stops, commas,
  question marks and capitals as you speak. Saying a mark yourself always
  wins, and a full stop that a mid-sentence pause put in is taken back out when
  the next phrase carries on ("and", "which", "to"...). "New paragraph" ends
  the sentence before it.
- **Four speech engines.** Moonshine (the default) and Whisper ship inside
  QUILL Lite and recognise English on the computer; Windows speech recognition
  can use any speech language installed in Windows; Windows voice typing hands
  over to Windows+H. Chosen after measuring eight candidates for accuracy,
  punctuation, speed on one processor core and size -- Moonshine was the most
  accurate and by far the fastest.
- **Spoken punctuation, layout and symbols** anywhere in a phrase: punctuation,
  quotes, brackets and braces, hyphen, dash, slash, backslash, underscore, at
  sign, hash sign, dollar and percent signs, ampersand, asterisk, plus, minus
  and equals signs, new line, new paragraph and tab. "Literal" in front writes
  the word instead.
- **Voice commands**, each as a whole phrase: scratch that, undo that, select
  that, capitalize that, all caps that, no caps that, delete word, delete
  sentence, read that, go to beginning or end of line, go to top, go to end of
  document, what can I say, stop dictation. The ones that change the last
  phrase refuse, and say so, if you have typed into it since.
- **Spelling mode**: "start spelling", then letters -- by name or with the
  phonetic alphabet -- with "capital" and "space", then "stop spelling".
- **The wake phrase**: say "Quill dictate", or a phrase of your own, to start
  dictation without the keyboard; anything said after it in the same breath is
  written. Off until you switch it on. It listens only while QUILL Lite is the
  window in front, drops everything that does not begin with the wake phrase,
  and closes the microphone when another program comes forward.
- **Your own words and phrases**: a vocabulary that corrects near misses to your
  spelling, and replacements (`say => write`) that are your own spoken phrases,
  in a file opened from Dictation Settings. The same format QUILL uses.
- **What can I say**: every phrase dictation acts on, in a window you can read
  with the arrow keys (say "what can I say", or press Dictation Commands in
  Dictation Settings), and as a published page, **Dictation commands** --
  both generated from the table dictation itself reads.
- **Dictation Settings** (**Alt+Shift+F6**): engine, Windows speech language,
  microphone by name, what you hear after each phrase (a sound, the words read
  back, both, or neither), what "dash" writes, the tones and words for on and
  off, and the wake phrase.
- **A Dictation cell in the status bar**: off, listening, hearing you, writing,
  spelling, or waiting for the wake phrase. Enter on it starts or stops
  dictation. Fourteen cells now, where there were thirteen.
- **Dictation is a feature area** in Customize Features, on by default and off
  in the WordPad and Notepad profiles. Switching it off closes the microphone.
  Twenty areas now, where there were nineteen.
- **QUILL has the same feature on the same keys** (Tools > Speech > Live
  Dictation), from the same shared code, and reads the same `dictation.md` its
  Locked Dictation uses.

### Five finer dictation choices, and Just write what I say

- **Just write what I say** (`windows_dictation_continuous`, off): a pause does
  nothing -- the engine's end-of-phrase full stop is removed and the next
  phrase continues the sentence (a capital earned only by the pause goes; "I"
  stays), no phrase tone, no read-back, and whole-phrase commands are written as
  words. Spoken marks and the stop phrase still work.
- **Automatic punctuation** on or off for Moonshine and Whisper
  (`windows_dictation_auto_punctuation`): off strips the engine's marks and the
  capitals they alone earned.
- **Pause before a phrase is written** (`windows_dictation_pause`: short 0.5 s,
  normal 0.8 s, long 1.4 s), handed to the voice detector, and to Windows
  speech as `ComplexResponseSpeed`.
- **Remove filler words** (`windows_dictation_remove_fillers`), word by word
  with QUILL's own filler lists, so punctuation stays with real words.
- **Stop after silence** (`windows_dictation_silence_minutes`: never, 1, 5, 10),
  checked every 15 seconds only while writing; spoken as "Dictation off after N
  minutes of silence."
- **Test Microphone**: four seconds on the chosen microphone; the peak level in
  words, and what Moonshine or Whisper heard; spoken and kept in a field.
- Dictation Settings is now **two columns**, so it fits a 768-pixel screen.
- `DictationPreferences` moved to `quill/core/windows_dictation/preferences.py`
  (re-exported from the controller); the choices live in `options.py`.

### Stop phrase

- **Choose your own stop phrase** in Dictation Settings (`windows_dictation_stop_phrase`,
  "stop dictation" by default). It stops dictation only when said on its own,
  forgives a near miss like the wake phrase, needs two words, and returns to
  standby when the wake phrase is on. "Stop dictation" always works as well. The
  commands list names the user's own.

### AI help on your own OpenAI key

- **Use My Own OpenAI Key** (Tools > AI, Alt+F2): a saved OpenAI key lifts every
  limit on AI help -- no allowance, no size ceiling -- and sends the passage
  straight to OpenAI on the user's account, with no QUILL server in between.
  There is no separate switch: the key's presence is the state, and **Remove the
  Saved Key** returns to the free service immediately. The window also has
  **Test the Key** (one tiny request, on a worker thread, result spoken) and a
  model box. Code `QUILL-AI-OWN-KEY-FAILED` when a request fails.
- **The same instructions** as the free service: the gateway's prompt templates
  are sent as the system message, and a test fails if the two drift.
- **One key store with QUILL**: Windows Credential Manager (an encrypted file in
  a portable copy), shared with QUILL's AI Hub.
- **QUILL has the same window on the same key**, in its AI menu, from the same
  shared module (`quill/ui/hosted_ai_own_key.py`).
- **Usage and About change with the key.** Usage opens its own window
  (`OwnKeyUsageFrame`): the model, no allowance, and Open My OpenAI Usage; no
  Sign Out, no support ID, and nothing fetched. About shows the model and the
  OpenAI usage address in place of the free allowance.
- **A model list, not a text box.** Filled from the account's `/v1/models`
  once the key is checked -- Test the Key, or opening the window with a key
  saved, so the model can be changed at any time. Luna 6 (`gpt-6-luna`) first,
  then the other GPT-6 models, then the rest by name; models that cannot answer
  text (speech, transcription, images, embeddings, moderation, `instruct`) are
  left out (`quill/core/ai/own_key_models.py`).
- **Estimated costs** on every row and in a Cost estimate box, labelled as
  estimates everywhere, with OpenAI's real pricing address. Rough tiers from the
  model's name; a typical request is 1,100 tokens in and 300 out.
- **Fixed: GPT-6 refused every request.** OpenAI's newer models answer HTTP 400
  to `max_tokens`; requests to OpenAI now send `max_completion_tokens`, which
  every OpenAI chat model accepts. Shared with QUILL's AI Hub, which had the
  same fault.
- Setting: `ai_own_key_model` (empty means the default model).

## 1.0.1 -- 2026-09-25

A fix for AI help on some Windows 10 computers.

- **Connecting AI help no longer fails with "could not reach the internet" on a
  computer whose internet is fine.** On some Windows 10 machines, Connect stopped
  at the step that gets your code, with error QUILL-AI-GATEWAY-OFFLINE. The
  connection had been made; QUILL Lite could not verify the AI service's security
  certificate, because it trusted only the certificates Windows had already
  downloaded, and Windows fetches most of them only when its own networking first
  needs one. QUILL Lite now also trusts the certificate authorities it ships with,
  so the check succeeds. Nothing about the check is weaker: every certificate is
  still verified.
- **When a connection does fail, it says which way.** A certificate that cannot
  be verified, an address that cannot be looked up, a connection refused, and a
  service that did not answer in time are now four different sentences, each
  naming the service and ending with the reason Windows gave -- where before all
  four were "could not reach the internet". New error codes
  QUILL-AI-GATEWAY-CERTIFICATE and QUILL-AI-GATEWAY-UNREACHABLE name the first
  and the last two.

## 1.0.0 -- 2026-09-25

First release. QUILL with everything removed except the editor: numbered
documents in one window, four kinds of document, and nothing else.

Contributed as [PR #1490](https://github.com/Community-Access/quill/pull/1490)
by Steven Scott (`doubletaponair`) under this repository's MIT licence, and
adopted into the QuillVille family here. Everything below is in 1.0.0,
assembled between 2026-09-08 and 2026-09-25.

Three lists, each grouped by subject: **Added** is what was not there before,
**Changed** is what worked differently, **Fixed** is what was wrong. The two
lists at the end are the QUILL side of the same work, because the rule that
governs this product is that QUILL Lite may never be ahead of QUILL -- so anything
the small editor needed that the big one could not do went into the shared code
in the same release.

### Added

#### Files, encoding and saving

- **Save an HTML page as Markdown.** The Save As box offers **Markdown
  (*.md)** again, and this time it converts: an HTML document saved as `.md`
  has its tags turned into Markdown as it saves -- `#` headings, `**bold**`,
  `-` lists, links that keep their text and address -- and QUILL Lite says
  "Converted HTML to Markdown". The document on screen changes with the file,
  so the window and the file never disagree. Tags Markdown cannot write are
  dropped and their text kept; a page that would convert to nothing is left
  exactly as it was and says so. Plain text and Markdown documents saved as
  `.md` are untouched. Rich text is not offered the row -- flatten to plain
  text first, which the dialog already asks about.

- **Earlier Versions** (**Ctrl+Alt+Shift+E**, File menu). QUILL Lite has written
  a dated copy of every save since backups shipped and gave you no way to read
  one: the files were correct, correctly named, and reachable only by knowing
  where the app keeps them. A safety net nobody can reach is a folder that fills
  up. The list reads "Today at 4:12 PM -- 2,341 words"; **Restore** puts a
  version into the window without saving, so Ctrl+Z takes it back and the file
  on disk is untouched until you decide, and **Open a Copy** puts it in a new
  window and leaves your document alone.

- **Byte-honest files.** Open, change nothing, save, and the bytes are the bytes
  you started with: the encoding is kept including a byte order mark, the line
  endings are kept, and a file that did not end in a newline does not grow one.
  UTF-8 is tried before Windows-1252 precisely because cp1252 cannot fail to
  decode, so trying it first would mean never detecting anything else.

- **Encoding and line endings on purpose** (Ctrl+Alt+E). The round trip is the
  default and this is the deliberate exception, for the person who needs a UTF-8
  copy of an old file or Unix line endings for a build server. It takes effect
  at the next save, which is the moment it means anything.

#### The four kinds of document

- **A plain document now has a language**, and it decides what the keys write.
  **Ctrl+B in a `.md` writes `**bold**`; in a `.html` it writes `<strong>`**,
  where both used to refuse and send you to rich text. Same for italic,
  underline and the six heading levels. `.html`, `.htm` and `.xhtml` are
  recognised; `.md`, `.markdown`, `.mdx` and `.txt` are Markdown; a `.py` or a
  `.conf` is plain and says so.

- **Format > Document Language (Ctrl+Alt+F6)**, and the status bar's Format
  cell, for saying the language is not what the file name implies.

#### Headings and structure

- **The Heading Organizer — Alt+Shift+O.** Every heading in the document
  in one list. Arrow through them, Tab to demote and Shift+Tab to promote, move
  a whole section up or down, rename one, and check the result against the
  accessibility rules for heading order. QUILL Lite could already list headings
  and already move sections; this is both at once, so you can hear the shape of
  the document change as you change it.

- **Folding over Markdown sections.** **Ctrl+Shift+F9** folds the section you
  are in and says how many lines went with it; **Ctrl+Alt+Shift+Down** and
  **Ctrl+Alt+Shift+Up** walk between sections, each one saying its heading,
  whether it is folded, and how long it is; **Ctrl+Shift+F10** opens
  everything again. Nothing is hidden from the cursor and a folded section reads
  exactly as it reads unfolded — this is a way of skimming, not a change to your
  document.

- **Lists announce themselves.** Arrow into a list and QUILL Lite says "Bulleted
  list, 5 items"; a level deeper, "Level 2, 3 items"; on the way out, "Out of
  list". This is the one cue a screen reader gives you everywhere else -- a
  browser hands it a list with a count, and an editor hands it characters.
  Markdown and HTML, over bullets, numbers and definition lists alike, with
  "Term" and "Definition" as you move between the two halves of a `<dl>`.
  Items are counted at your own level inside your own list, never totalled.
  **View > Announce Lists (Ctrl+Alt+F5)** turns it off and on where you stand.

- **Headings announce themselves.** Arrow onto a heading and QUILL Lite says
  "Heading 2". It has to say it, because no Windows edit control exposes a
  paragraph style to a screen reader -- JAWS and NVDA could see the font size
  and the weight and nothing else, so a heading read out exactly like body text.
  The level only, once on arrival, and in both rich text and Markdown.

- **Heading navigation works in plain text.** Next Heading, Previous Heading and
  the headings list refused outright in a plain document -- "Headings are only
  available in rich text" -- in documents whose Markdown headings Alt+Shift+Right
  would happily re-level. They now walk the hashes, and a `#` inside a fenced
  code block is correctly not a heading. The status bar's **Heading** cell read
  "Not in rich text" in those same documents -- wrong twice over, since pressing
  Enter on it has always opened a working list of them -- and now reads the
  level.

- **View > Announce Headings (Ctrl+Alt+F3)** turns the cue off and back on where
  you stand, saying which way it went rather than "on" and "off". Reading a
  document as text is a different job from writing one.

- **A `#` is only a heading where `#` means heading.** A `.md`, a `.txt` or an
  untitled buffer has Markdown headings; a `.py`, `.sh`, `.ini`, `.yml` or
  `.conf` does not, because there a leading `#` is a comment -- and QUILL Lite is
  the editor people open build scripts in.

- **Format ▸ Headings**, with **Heading 1 to 6** on Ctrl+Alt+1 to Ctrl+Alt+6 and
  Body Text on Ctrl+Alt+0. Line spacing moved into **Format ▸ Line Spacing** in
  the same tidy-up.

- **Format ▸ Structure**: **Promote Heading** and **Demote Heading**
  (**Alt+Shift+Left** / **Right**), **Move Section Up** and **Down**
  (**Alt+Shift+Up** / **Down**). QUILL Lite could make headings and walk between
  them but never move them, which left cut-and-paste as the only way to
  reorganise -- the operation it is worst at, since moving a section by hand
  means selecting to a boundary you cannot see and usually costs you your place.
  QUILL's own four keys. Section moves work in plain text, where headings are
  Markdown; promoting and demoting work in both modes.

#### Selection and marks

- **Extend Selection Mode — Alt+Shift+F9.** A Shift that stays down: press
  it, move by any means you like, and the selection follows without you holding
  a modifier — and without your screen reader saying "selected" on every single
  arrow press, which is what makes Shift+Down unusable for taking four
  paragraphs. QUILL Lite tried this once before and it did not work; this is
  QUILL's version, which does. **Ctrl+Alt+F8** is now the F8 *marker* toggle,
  which is a different thing and used to share the key.

- **Review Buffer (Alt+Shift+U)** opens a copy of what you have selected, in a
  window of its own, that cannot be edited. The point is what you cannot do in
  it: reading a long selection back means arrowing through it, and arrowing
  through your own document with a selection live means the next character you
  type replaces all of it. QUILL has had this and no key for it; it has one now
  too, the same one.

- **Structural selection.** Select the word, the line or the paragraph, or press
  Ctrl+Shift+X to expand outwards -- word, line, sentence, paragraph, block,
  document -- with the scope announced each time. Shift+arrow selects by
  character, which is the right tool for two letters and the wrong one for a
  paragraph.

- **A Selection submenu under Edit**, and it is three features rather than one. *Mark and
  extend* (F8 anchors, any navigation key extends, Shift+F8 completes,
  Ctrl+Shift+F8 reselects, Alt+Shift+F8 goes to the start) is the only way to
  take an arbitrary run without holding a modifier down the whole way.
  *Structural* selection takes the word, line, paragraph, sentence or block in one
  keystroke, and Expand/Shrink walk the ladder in both directions. *Marks* are
  throwaway positions -- deliberately not bookmarks, which are the ones you mean
  to keep -- with set, pop, list and exchange-with-cursor.

  Every one of them announces **how much** it took. A selection that says
  nothing is one the user has to test by pressing something destructive, and
  the count is the whole difference between "I have it" and "I think I have it".

  Select All keeps its place in the Edit menu on Ctrl+A, so switching this whole
  area off never removes it.

#### Navigating, bookmarks and going back

- **A temporary bookmark** -- **Ctrl+Alt+J** drops a pin where the cursor is and
  **Ctrl+Shift+J** goes back to it. Use it when you are about to go and look
  something up and want to come straight back. It has no number, no label and no
  row in the bookmark list, setting it again simply moves it, and it is gone when
  the document closes. QUILL has had these two keys for years; they now mean the
  same thing here.

- **Ctrl+G is Go To, not just Go to Line.** One window with a target kind --
  Line, Bookmark or Heading -- the way Word has always done it. A number field
  for a line, a list of places for the other two, and arrow keys move between
  the kinds. Alt+Shift+G and Ctrl+Alt+L still go straight to the bookmark and
  heading lists, which is faster when you already know which you want; this is
  the key to press when you do not. Bookmark rows are led by their digit and
  heading rows by their level, so you can pick one out by its first word.

- **Bookmarks and your place in the file survive closing the document.** The
  reason to have numbered bookmarks at all is that there is no scrollbar thumb
  to glance at in a long file -- and that does not stop being true when the
  window closes. Marking nine places and losing them on the way out is the same
  loss, deferred. Reopen a file and the bookmarks and the cursor are where you
  left them; a document you have never saved is not remembered, because there is
  nothing stable to key it by, and nothing is ever written next to your own
  files. Switching bookmarks off in Customize Features stops it being written at
  all.

- **Go Back and Go Forward** -- **Alt+Left** and **Alt+Right**, in the Edit
  menu. The undo for moving about. Every jump is remembered: going to a line,
  following a heading, picking from the heading or bookmark list, landing on a
  search hit. Without it, pressing F3 to check a word elsewhere is a one-way
  trip, and finding your way back means knowing a line number you were never
  told.

- **Nine numbered bookmarks** that move with the text as you edit around them --
  a bookmark that is wrong is worse than one that does not exist, because it is
  trusted. Ctrl+Shift+B drops one, Ctrl+Shift+1 to 9 set a numbered one, F2 and
  Shift+F2 walk them, Alt+Shift+G lists them.

#### Spelling

- **List Misspellings (Alt+Shift+L)** shows every one at once with the line it
  is on, and Enter goes there. Ctrl+F7 answers "where is the next one"; this
  answers "how many are there, and which do I want". Words you have ignored are
  left out.

- **A spelling context menu.** With the caret in a misspelled word, the
  Applications key opens with the corrections at the top -- then Ignore Once,
  Ignore in This Document, Add to My Dictionary, Add to This Document Only, and
  the way on to More Suggestions, Check Document and Next/Previous Misspelling
  with their keys. Every row names the word. A correctly spelled word gets the
  ordinary edit menu, and that menu keeps everything Windows put in it.

- **Tools ▸ Spelling ▸ Announcements (Ctrl+Alt+Shift+F7)**: twelve settings for
  how a misspelling is said. Whether the sound plays, whether the word is spoken
  too, how long before the same word is reported again, whether words are
  spelled out and after how long, and whether the letters come plainly, in the
  phonetic alphabet, or both. An example box says what your choices sound like.

- **Ctrl+F7 now spells the misspelling it lands on**, after a pause. "receive"
  and "recieve" are the same sound, so hearing the word tells you nothing; the
  letters are the answer. Press the next key and the spelling is cancelled
  unheard.

- **Spell check**, which neither Notepad nor WordPad had when this editor's
  keyboard was designed -- WordPad never gained one at all, and Notepad only in
  2024. QUILL's dictionary, QUILL's suggestions and QUILL's guided review: F7
  reviews the document, Shift+F7 suggests for the word at the cursor, Ctrl+F7
  and Ctrl+Shift+F7 move between misspellings and *select* them so the word is
  what the reader reads on arrival, and Alt+F7 teaches it.

  The load-bearing part is where it does **not** speak. Spell check while typing
  is off by extension in source and configuration files
  (`quill.core.spellcheck_filetypes`), because every identifier in one is a word
  no dictionary has and each false alert costs a status line to read past --
  the cost a sighted user pays for a red underline and a screen-reader user pays
  in full. Markdown is prose and is checked; its fenced blocks and code spans
  are suppressed by region instead. The state is per document, so a letter and
  a config file open together can honestly disagree, and Ctrl+Alt+F7 changes
  only the one you are in. Opening a skipped file says so once: a checker that
  is silently off is indistinguishable from one that is broken.

  Taught words live in QUILL Lite's own folder unless Preferences says to share
  QUILL's, for the same reason the abbreviation switch exists and defaults the
  same way. A document may also carry its own `.quill-dict.json` sidecar.

#### The clipboard, the tray and the collector

- **Copy All (Ctrl+F8)** puts the whole document on the clipboard without
  selecting it. Select All then Copy is two keys and leaves everything selected
  afterwards, so the next character typed replaces the document.

- **Copy to Tray Slot... (Alt+Shift+Y)** lets you choose which of the twelve
  slots to copy into, with each row saying what is in that slot now. Ctrl+Alt+Y
  still takes the next free one.

- **The clip library can fill itself.** Preferences has a new switch, **Keep
  everything I copy in the clip library**, and with it on every copy and every
  cut made inside a QUILL Lite document is remembered, up to the last two
  hundred. It is off until you ask for it: a history of everything you copy is a
  file on your disk holding whatever you last took out of a document. The help
  text in Preferences says so. Until now the app promised this history in three
  places and never kept any of it -- only Keep Clip ever put anything in the
  library.

- **Three answers to a clipboard that holds one thing.** A twelve-slot copy tray
  that survives a restart; a collector that gathers several copies into one
  buffer; and a rolling clip library that remembers what was copied whether or
  not you decided at the time that it mattered. Plus Ctrl+Shift+V, which pastes
  text with none of its formatting.

#### Lines and text tools

- **Quote Lines (Ctrl+Shift+Q)** and **Remove Quote Marks (Alt+Shift+.)**,
  for replying to email and quoting a log excerpt. (Remove Quote Marks was
  on Ctrl+Alt+Shift+Q until 1.2.0.)

- **Hard Wrap Lines (Alt+Shift+W)** asks for a width and re-flows to it, keeping
  paragraphs apart and never breaking a word. This changes the document, unlike
  View, Word Wrap.

- **Delete Lines Containing (Alt+Shift+X)** removes every line with what you
  typed in it -- taken literally, not as a pattern -- and says how many went.
  One Ctrl+Z takes them all back.

- **Convert to Spaces (Alt+F11)** and **Convert to Tabs (Alt+F12)** in Tools,
  Indenting: the single most common change anybody makes to somebody else's
  file.

- **Line Statistics (Ctrl+Alt+W)** says the longest line, which line it is, and
  the average, which is what you want when formatting for a braille display or
  a narrow window. Document Statistics answers how big; this answers how wide.

- **Numbered lists, at last.** **Ctrl+Shift+L** rings rather than toggles:
  bulleted list, numbered list, no list, round again, which is what WordPad's
  own button on that key does. It works in rich text -- where the control draws
  the markers and renumbers them as you add items -- and in Markdown, where it
  writes `- ` and `1. ` on the lines you selected and nowhere else.

- **Toggle Line Comment (Ctrl+/).** QUILL Lite is where people edit a `.py`, a
  `.conf` or a bit of JSON -- it already keeps the spell checker quiet in them --
  and commenting a few lines out is the other half of that. The prefix follows
  the file name: `# `, `-- `, `<!-- -->` or `// `, the same rule QUILL uses.

- **Describe Indent Depth** (**Ctrl+Alt+Shift+V**, Tools ▸ Indenting). How far
  the current line is indented: "4 spaces", "1 tab", "1 tab, 3 spaces". A screen
  reader reads a line's words and not the whitespace in front of them, so in a
  YAML or Python file the structure of the document is not there when you listen
  to it -- and it also tells you the thing nothing else will, that this line is
  indented with a tab while its neighbours use spaces. Added to QUILL first, on
  the same key, because QUILL Lite may never be ahead of the editor.

- **Tools.** Sort lines, remove blank lines, remove duplicates, trim trailing
  spaces, and UPPERCASE / lowercase / Title Case -- each on the selection if
  there is one and the document if not, and each a single undo step, so Ctrl+Z
  takes back the whole sort rather than forty separate line moves.

#### The Insert menu

- **An Insert menu**, before Format, holding what used to be Edit > Insert plus
  three new rows. Every existing key is unchanged.

- **Insert > Emoji (Alt+.)** -- QUILL's picker, key for key: search by name,
  keyword, description or a typed smiley, browse by category, and read a
  written description of every glyph. In every document, rich text included.

- **Insert > Markdown Tag (Ctrl+Alt+I)** and **Insert > HTML Tag
  (Ctrl+Alt+O)**. Exactly one is ever live -- whichever the document is -- and
  the other is dimmed rather than hidden, so a reader is told it is unavailable
  rather than left hunting for it. The HTML picker searches by what a tag
  *does*: "dropdown" finds `select`, "checkbox" finds `input`.

- **Whole form fields in the HTML picker** -- twenty of them, each arriving
  labelled and wired: a `for` that matches the field's `id`, a `name` that
  submits, options inside a select, a legend inside a fieldset, one shared
  `name` across a radio group, and `aria-describedby` joining a field to its
  hint and its error. The `id` is checked against your document first, so a
  second email field is `email-2` rather than a silent duplicate. Select a word
  and it becomes the label, with the `id` derived from it so the two agree.

- **The HTML picker now offers 111 tags**, up from 46. The forty-six left out
  `<dl>`, `<dt>` and `<dd>` -- which this editor *announces* as you arrow
  through them -- along with `<figure>`, `<figcaption>`, `<caption>`, `<thead>`,
  `<tbody>`, `<abbr>`, and `<br>` and `<hr>`, which were handled as void
  elements and simply could not be chosen. A searchable list should be
  complete: searching 111 is no harder than searching 46, and a missing tag is a
  dead end.

- **The Markdown picker gained Underline, Horizontal Rule, Strikethrough and
  Definition List.** The first two had builders and no menu row for months.

- **Insert Link (Ctrl+K).** Word's key, and everybody's. Select the words, press
  it, type the address: `[text](address)` in a Markdown document,
  `<a href="address">text</a>` in an HTML one. QUILL Lite had both kinds, a tag
  picker for each, and no way at all to make the one tag everybody inserts.

- **Insert > Line Break (Shift+Enter).** Ends the line without starting
  a new paragraph -- the distinction a blank line cannot make, and the chord
  Word uses for the same thing. QUILL Lite says which spelling it wrote, because
  the older one (two trailing spaces) is invisible on screen and silent to a
  screen reader. **Markdown line break style** in Settings chooses; the default
  is a backslash.

- **Insert > Special Character... (Ctrl+Shift+F2).** A searchable picker
  for the 357 characters a keyboard has no key for. Type part of a name
  (`dash`, `euro`, `acute`, `arrow`) or a word Unicode does not use but people
  do (`gbp`, `copyright`, `eszett`), or clear the box and browse one of fifteen
  groups: whitespace, dashes and hyphens, quotes, invisible and control,
  typography, legal and reference marks, currency, maths and units, fractions,
  superscripts and ordinals, arrows, accented letters small and capital, Greek
  letters, and punctuation from other languages. Each row shows the character,
  its name and its code point, with a description pane that updates as you
  arrow. Enter inserts, and QUILL Lite reads back what it put in -- "Inserted --
  U+2014 Em dash" -- because most of the list is invisible on the page and the
  reader says nothing when an app writes text on its own behalf. The search box
  is also a code-point box: `2014`, `U+2014` and `d8212` all find the em dash,
  and a code point in no group still resolves, so the picker reaches every
  character Unicode has. QUILL has the same picker on the same key,
  **Ctrl+Shift+F2**.

  **Insert Date and Time moved with it**, from Edit to **Insert > Date and
  Time**. Its key is still **F5**.

#### Typing, characters and the control's own keys

- **Overwrite mode**, with a **Typing Mode** cell in the status bar
  (**Ctrl+Alt+Shift+W**). A mode you cannot ask about is one you discover by
  typing over your own work. The **Insert** key still works, because the editing
  control answers it whether QUILL Lite asks or not -- QUILL Lite watches for it
  rather than claiming it, since Insert is NVDA's and JAWS's own modifier, so
  the cell stays right either way.

- **Tab Key Inserts a Tab Character** (**Ctrl+Alt+Shift+I**), with a **Tab
  Mode** status cell. QUILL Lite starts where Notepad does -- Tab types a tab --
  and clearing the tick makes Tab indent the line instead, announcing the new
  depth. **Shift+Tab** outdents in either mode, so a tab typed by accident is
  always one keystroke away from being undone.

- **Describe Character** (Ctrl+Shift+C). Exactly which character the cursor is
  on: its name, its code point, and the plain-language note for the invisibles
  that bite writers. A screen reader says "space" for four different characters,
  and this is the only way to tell which one broke the search.

#### Abbreviations and snippets

- **Snippets — Ctrl+Alt+Shift+Home.** (It was Alt+Shift+I until 1.2.) A list
  of every abbreviation, most used first, with a preview of what each one writes. Abbreviations expand when you
  type the trigger, which is perfect for the six you use daily and no help at
  all for the fortieth one, whose trigger you cannot remember.

- **Tools ▸ Expand Abbreviations (Alt+Shift+A)** turns expansion off and on
  from the keyboard, with a tick showing which way it is set. Expansion is the
  one feature that acts *while you type*, so the moment you want it off is
  usually the moment it has just expanded something you meant to keep -- and a
  dialog three keystrokes away is three too many. It is the same switch as the
  Abbreviations box in Customize Features.

- **Abbreviations.** QUILL's own engine and manager dialog, over QUILL Lite's own
  library. A switch in Preferences -- off by default -- points it at the library
  QUILL and Quill Inkwell share instead. Off by default because a machine that
  has never had QUILL installed must not grow a Quill data folder because
  somebody opened a text file.

#### The status bar

- **A List cell on the status bar**, which says which item you are on as well
  as which list you are in -- the one thing the speech deliberately does not.

- **View ▸ Status Bar (Alt+Shift+B)** hides and shows the status bar, the way
  Notepad's has since Windows 95. Nothing is lost while it is away: Ctrl+Alt+W
  speaks the counts and Ctrl+G asks for a line. Pressing **F6** with the bar
  hidden says so rather than doing nothing -- and F6 itself is now listed in
  **Navigate ▸ Status Bar**, because going there is a move, not a setting.

- **A status bar that can be read.** Ten focusable cells on QUILL's own model:
  F6 lands in it, the arrow keys and Home/End move between them, Enter acts on
  the cell, and Escape returns to the document. The last message, the position,
  words, characters, the selection, the mode, the heading you are in, the
  encoding, the line endings, and whether anything is unsaved.

  Two of those are facts no editor most people have used shows at all --
  encoding and line endings -- and they are exactly what decides whether a file
  survives a round trip. Refreshes are coalesced through a 90 ms timer (QUILL's
  own window), because counting words is O(document) and doing it per keystroke
  is felt while typing.

#### Speech, sounds, and how much it says

- **A pause between spoken messages.** Preferences has **Shortest gap between
  spoken messages**, in milliseconds, and setting it stops QUILL Lite saying
  things faster than you can hear them -- which is what a held-down key used to
  do. Zero, the default, is what it has always done. Nothing is lost by turning
  it up: the status bar is written either way, and F6 reads it back.

- **Sound works at all.** Two bugs meant no earcon in either editor had ever
  played: the sound pack was never loaded (the manager reloads only when the
  pack path *changes*, and the default path equals its own initial value), and
  the audio backend freed each sound before it could be heard. Both fixed.

- **Earcons for the ordinary moments**: app start and exit, document new, open,
  save and close, printing, cut, copy, paste, delete, undo, redo, nothing left
  to undo, abbreviation expanded, autocorrect, search found, not found and
  wrapped, and errors. These are the moments a screen reader says nothing about,
  which is what makes a sound the only feedback they can have.

- **The Sound Scheme window lists twenty-two events, not a hundred and forty-one
  -- and every one of them fires.** It used to list the whole catalogue, most of
  which QUILL Lite never posts.

- **Tools ▸ Sound Scheme (Ctrl+Alt+Shift+O)**: every sound QUILL Lite can make,
  in a list that plays each one as you arrow onto it. Per event: Play, switch it
  off, Browse for a WAV of your own, No Sound, or Use Default. Save the set as a
  scheme of your own -- an ordinary folder you can copy or send -- and Restore
  All Defaults always works, because the shipped sounds are never overwritten.
  The same window QUILL opens, over the same schemes.

- **A sound when you type a misspelling.** QUILL Lite had none at all: the alert
  was a line in the status bar, which on a bar nobody is watching is not an
  alert.

- **Speech to NVDA and JAWS only.** No self-voicing fallback: a second voice
  talking over a screen reader is worse than silence. Only outcomes are
  announced -- a save, a wrapped search, a formatting change -- because titles,
  focus moves, control names and selections are the reader's to say. Everything
  spoken also lands in the status bar, so a missed message can be read again.

#### Printing

- **Print Preview — Ctrl+Alt+Shift+P.** Not a picture of a page. How many pages,
  on what paper, with what margins, and what is at the top of each one — the
  questions a picture of a page was never going to answer for you.

- **Rich text prints as rich text.** A rich document is now printed by the text
  control itself, so headings are headings and bold is bold on paper. It used to
  print as flat text.

- **Printing** (Ctrl+P) and Page Setup. Long lines wrap to the page whatever the
  Word Wrap setting says, because a printed line that runs off the paper is gone
  rather than scrolled to.

#### Windows, sessions and recovering unsaved work

- **A say in what reopens — File ▸ Reopen Last Session... (Alt+Shift+F12).**
  QUILL Lite reopened last session's documents without asking and skipped one whose
  file had gone without saying so. Right for one document, wrong for four: four
  windows appearing unbidden is four things to identify before you can start, and
  a file that has *moved* is the case where silence is worst — nothing opened,
  nothing said, and no way to tell that from "it opened and I have not found it".

  It asks **when it matters** now: one or two documents that are all still there
  open as before; three or more, or anything missing, gets a window listing what
  was open with a checkbox on each row. **Open Checked**, **Open All**, **Not
  Now** (Escape, and it changes nothing), **Forget Checked**, **Clear the List**,
  **Never Ask Again**. Forgetting only removes a row from the list — no file is
  ever touched, and the window says so under the buttons rather than in a warning,
  because a warning on a harmless action teaches people to click through the ones
  that matter. Afterwards you hear the count: "Reopened all 3 documents",
  "Reopened 1 of 2", "Forgot 2 documents. 1 still remembered."

  The same window, the same key and the same setting in QUILL, from one shared
  core (`quill/core/session_restore.py`). Three answers live in preferences:
  always ask, ask when it matters, or never ask.

- **Ctrl+F4 closes the document**, the key Windows has used for a window inside
  a window since 3.1. Ctrl+W always did; Ctrl+F4 did nothing.

- **Numbered documents in one window.** Documents open as numbered children of
  one QUILL Lite window, and a number never changes while that document is open
  -- so "document 3" stays a name a person can hold rather than "the other
  Untitled". Alt+1 to Alt+9 jump straight to one, Ctrl+Tab and Ctrl+F6 walk
  them, and the Window menu lists them all with a mark on the one you are in.
  The title carries the number, because that is the one string a screen reader
  reads on arrival.

  The cost is recorded rather than hidden: documents inside one window do not
  appear in Alt+Tab, so those four routes carry the whole job of moving between
  them, and all four are bound rather than one.

- **Unsaved-work recovery.** A copy of every modified document written aside on
  a timer, beside your file and never over it, offered back on the next launch
  and deleted the moment you save or close cleanly.

- **Session restore.** Reopen the documents that were open last time, in the same
  numbered order. Distinct from recovery, which is only ever about work that was
  never saved.

#### Menus, keys and the palette

- **Notepad's and WordPad's keys, unchanged.** Ctrl+N, Ctrl+O, Ctrl+S,
  Ctrl+Shift+S and Ctrl+P; Ctrl+F, F3, Shift+F3, Ctrl+H and Ctrl+G; F5 for the
  date and time; Ctrl+B, Ctrl+I and Ctrl+U; Ctrl+L, Ctrl+E, Ctrl+R and Ctrl+J
  for the four alignments; Ctrl+1, Ctrl+5 and Ctrl+2 for single, one-and-a-half
  and double spacing; Ctrl+Shift+L for bullets; Ctrl+Shift+> and Ctrl+Shift+< to
  grow and shrink; Ctrl+=, Ctrl+- and Ctrl+0 for zoom. Somebody moving from
  either should not have to learn anything.

- **The Command Palette** (Ctrl+Shift+P), which answers "how do I sort lines?"
  rather than "what is under Format?", and shows each command's key beside its
  name -- which is how a key gets learned.

#### Features, profiles and preferences

- **Customize Features gained a Markdown and HTML area** (18, not 17).

- **The feature profile is in Preferences too**, at the top: the same four whole
  answers (Recommended, Everything, WordPad, Notepad) with a read-only box that
  says exactly what each would change. Customize Features is named after a
  mechanism; "make this Notepad" is a preference.

- **Customize Features** (View menu). Whole areas can be switched off -- rich
  text and the Format menu, headings, bookmarks, the Tools menu, the clipboard,
  printing, abbreviations, spell check, the Selection submenu -- and switching
  one off removes its menu *and* its
  keys, because a key that still fires for a feature you turned off is the
  feature not being off. This is how QUILL Lite stays a small editor without
  being a poor one.

  Four areas ship switched off and are found in the same list rather than
  hidden: autocorrect (welcome in prose, actively wrong in a config file),
  timestamped backups (reassuring, and they fill a folder), Go To Anything, and
  AI help, which is off because it sends what you ask about over the internet.

- **The theme follows Windows,** view-only and stripped back to automatic colour
  before every save, so a theme can never land in a document you send somebody.
  QUILL Lite shipped defaulting to dark on the grounds that its users are
  disproportionately light-sensitive. True, and it does not follow that they
  want *dark*: high-contrast black on white is a real requirement that a dark
  default breaks in exactly the same way. `system` does not guess, and it also
  settles the original complaint, which was never about which colour but about
  QUILL and QUILL Lite looking like two different editors on day one. Anybody
  who actually chose dark keeps it -- the settings file stores only what you
  changed, so a changed default reaches the people who never chose and nobody
  else.

#### Help, F1 and tutorials

- **Tutorials — Ctrl+Alt+F1.** Nine guided lessons in two tracks: opening a
  file and getting it back unchanged, the four kinds of document, numbered
  documents, what to press when you are lost — then selecting more than a few
  words, finding your way back, skimming something long, spelling without a red
  squiggle, and asking a question about the document in front of you. About
  forty-two minutes in all.

  Each lesson is a list of steps, and each step says what to press, **why**, and
  what you should hear when it worked. A step shows *your* key rather than the
  one QUILL Lite ships with, can run itself for you, and the window remembers
  where you stopped.

  Eight, and not more. QUILL has twenty-one in six tracks because QUILL is an
  environment you move into; a Notepad replacement with a twenty-one-lesson
  course attached is advertising that it is not one.

  The same lessons are also a document, beside the user guide, generated from
  the same source — so the book and the window cannot disagree.

- **Get Help from Support (Ctrl+Alt+F2).** QUILL Lite shipped with no way to
  report anything: only an address printed in the About box to copy out by
  hand. Help > Get Help from Support... now opens a short form -- what kind of
  message this is, a subject, what happened, and optionally what you expected
  and how to reproduce it -- and hands the finished message to **your own mail
  program**, addressed to support@community-access.org, with QUILL Lite's
  version, your Windows version and your screen reader already filled in.

  Your email address is optional: you can report a problem without giving one,
  you simply cannot be replied to. Nothing leaves the machine until you send it
  yourself, and QUILL Lite says so out loud rather than claiming to have sent
  something it has not. On a machine with no mail program set up -- webmail
  only -- the whole message and the address go to the clipboard instead, so
  nothing typed is lost. Writing to support@community-access.org directly works
  exactly as well; there is no form anybody has to use.

  The family's old reporting item filed a **public GitHub issue** through a
  token baked into every installer, which published whatever the reporter
  mentioned -- their configuration, their employer, the document they were
  working on -- permanently and searchably, and left them no way to be answered
  without a GitHub account. That transport is gone everywhere, not just here.

- **F1 everywhere.** What this window is for, then what the control you are on
  does, through the family's shared engine. Gated by GATE-LITE-HELP, plus a
  stricter QuillLite-only check that covers the two things the shared scanner
  cannot see: checkboxes, and the document control itself.

#### Settings, data and where it lives

- **Tools > Back Up Settings... (Ctrl+Alt+F11)** and **Tools > Restore
  Settings... (Ctrl+Alt+F12).** Write your configuration to a `.qsf` file
  and put it back on another machine. What describes *this* computer -- the
  recent-files list, the restored session, the window size, the update
  timestamp -- is deliberately left out, so a restore cannot point QUILL Lite at
  files that are not there. Restoring says what came across, what has been added
  since the file was written, and what was left alone.

- **Its own data folder** (`%LOCALAPPDATA%\QuillLite`), deliberately not
  `%APPDATA%\Quill`. Uninstalling does not remove it: recovered work is the one
  thing somebody may not have finished with, and an uninstaller is the worst
  moment to discover that.

- **A settings file that only records what you changed.** A fresh profile's
  `settings.json` is `{"schema": 1}` and nothing else. That is not tidiness: a
  file that spells out every field freezes today's defaults into every user's
  profile forever, so a later version that changes the default theme would leave
  behind exactly the people who never expressed a preference. Writing deltas is
  what QUILL's versioned-store contract buys, taken directly.

#### Downloads, updates and packaging

- **Check for Updates (Ctrl+Alt+U).** QUILL Lite shipped with no way at all to
  learn that a newer version existed -- the app most likely to be somebody's
  only Quill product, and the one whose users are least likely to go looking on
  GitHub. Help ▸ Check for Updates... now opens on **what changed** in the newer
  version, with **Update** and **Close** beside it, and offers to install and
  restart for you when the download finishes. Nothing downloads until you press
  Update. It is the same key and the same window every other app in the family
  uses.

- **A quiet daily look, off by one tick.** QUILL Lite also checks once a day when
  it starts and says nothing unless there is something -- not while it checks,
  not when there is nothing, and not when the network is down. Settings ▸ "Look
  for updates when QUILL Lite starts" turns it off; Ctrl+Alt+U still works.

- **An application icon of its own.** A white page with a folded corner and two
  amber lines of writing, on a forest-green tile. Every other glyph in the
  family is round, pointed, or built from bars, so this is the only one that
  blurs to a rectangle with a bite out of it -- which is the test that matters,
  because the other one is 16x16 in a taskbar. Generated by
  `scripts/build_app_icons.py` like every sibling, and gated so it cannot
  silently become a copy of another app's face.

- **Four release artifacts** on the family contract -- full installer, thin
  installer, portable zip and companion zip -- sharing the QuillVille Runtime,
  with neither ffmpeg nor libmpv staged because QUILL Lite has no media pipeline.

- **An optional file association.** The full installer offers *Open with
  QUILL Lite* for `.txt` and `.rtf` as a component, never as the default handler.
  An editor that quietly takes over every `.txt` on a machine is an editor
  people uninstall.

#### Documentation and QA

- **A sign-off checklist** ([`docs/qa/quilllite-signoff.md`](https://github.com/Community-Access/quill/blob/main/docs/qa/quilllite-signoff.md)):
  89 numbered steps for a person at a keyboard with a screen reader, each saying
  what to press and what decides pass or fail, with a fifteen-minute subset named
  at the top. It exists because everything a machine can check here is already
  checked -- and what somebody actually *hears* is not one of those things.

#### AI help (2026-09-23)

QUILL Lite gained five AI commands -- **summarize**, **rewrite**, **proofread**,
**explain**, and **ask a question about the document in front of you** -- running
on QUILL's own free service. They are in **Tools > AI**, behind **Ctrl+Alt+G**
(the assistant pad) and **Ctrl+Alt+Z** (the question box), with **Usage**,
**Connect or Sign Out** and **Privacy Agreement** beside them.

**Neither the feature switch nor the sign-in is enough to send anything.** Both
the area and the agreement have to be true. They are deliberately separate
questions: the area answers "does this feature exist in my copy", and the
agreement answers "have I agreed to what it does". Conflating them gets one of
them wrong -- an area switched on by a profile, by a settings import, or by
somebody else using the machine is not consent.

So the agreement is asked for on its own, stored as a **version** rather than a
yes, so that a material change to what is sent or kept can ask again instead of
the old answer being taken to cover the new thing. It is reachable by three
doors -- **Tools > AI > Privacy Agreement**, a tick box in **Preferences**, and
switching the area on in **Customize Features** -- because the place somebody
looks depends on which part of the app they already know. All three read and
write the same answer, so none of them can disagree with the others.

**How much you can ask about doubled.** The input ceiling went from about
1,125 words to about **2,250** (1,500 tokens to 3,000). Input is the cheap half
of a request -- the answer costs more to generate than the question costs to
send -- so the wider ceiling makes most short documents fit whole for a modest
increase per request. The service's own headroom was raised to match, because
running out of it turns hosted AI off for everyone rather than merely slowing it
down.

**Privacy Agreement is never dimmed**, whether or not the area is on and whether
or not you have accepted. A door you can only reach by first agreeing to
something is not a door.

**One pad behind one key, not five commands.** The chords free in *both* editors
are few, and family rule 2 says a command both products have keeps its chord --
so five separate keyed commands were never on offer. One pad is the better shape
anyway: one place showing what will be sent, one showing what is left, and one
consent surface rather than five.

**QUILL's existing AI is untouched.** No provider list changed, no default
cascade changed, and no bring-your-own-key, agent or local-model path changed.
The capability is shared, so the two editors run the same five commands on the
same five chords from the same module -- QUILL Lite is not ahead of QUILL here,
and QUILL has more AI than QUILL Lite rather than less.

#### Release day (2026-09-25)

- **The name is QUILL Lite**, everywhere you see or hear it: window titles,
  dialogs, About, help, the installer and its shortcuts. The program file, the
  settings folder and the downloads keep their old names, so an upgrade keeps
  everything you have set, and the installer removes the old shortcuts.
- **Connecting takes one keystroke.** The Connect window opens on your code,
  with **Open the Connect Page** filling it in for you in the browser; accepting
  the agreement goes straight there. Connecting no longer fails at once with
  "server_error", and Connect or Sign Out and Usage no longer fail to open.
- **Every AI window closes with Escape**, every sentence in them is reachable
  with Tab, and an error takes focus so it can be read again. Usage opens on
  your allowance.
- **Your allowance explains itself.** A new connection's smaller allowance for
  its first 48 hours says what it is and when it ends, today's number never
  reads higher than the month's, and Help > About shows your usage and support
  ID. Get Help from Support includes the support ID automatically.
- **Reading the agreement again is safe.** Privacy Agreement, once you have
  agreed, opens with **Keep Using AI** as the default; withdrawing is its own
  button. It used to withdraw the moment you pressed the key.
- **An untouched document closes without asking to save.** Rich Edit reports a
  change for things that change nothing, such as Ctrl+Z with nothing to undo.
- **A new AI guide** explains every command, exactly what is sent, and how the
  allowance works.

#### The last pass before 1.0 (2026-09-24)

- **Ask Me Next Time**, beside Never Ask Again in the Reopen Last Session
  window. Never Ask Again was the one answer in that window that could not be
  taken back: it set the preference to *never*, nothing else in either editor
  wrote that preference back, and the button's own help text sent you looking
  for a setting called "Reopen last session", which is a different setting doing
  a different job. So the window stopped appearing and there was no supported
  way to bring it back -- from a button people press in a hurry, which is
  exactly the population that then wants it back. Exactly one of the pair is
  enabled at a time and the other is greyed rather than hidden, so arriving on
  it tells you which way the setting is. Shared, so QUILL gained it in the same
  change.

- **Follow me is greyed in QUILL Lite**, rather than sitting there doing nothing.
  The tutorial window's Follow me watches the app's live state and moves you on
  when it can see you did the step; none of QUILL Lite's nine lessons carries a
  check, because every step here ends in a sentence the editor already says out
  loud. A tick box that can never do anything is one somebody ticks, waits on,
  and concludes is broken. Disabled rather than removed, so somebody who used it
  in Quill Radio is told it is unavailable instead of hunting for it.

#### Normal Text (2026-09-22)

- **Normal Text** (`Ctrl+Shift+N`), Word's command for taking formatting back
  off -- the only thing in the Format menu with no way to reach it.

### Changed

#### Files, encoding and saving

- **A UTF-16 big-endian file stays big-endian.** Both byte orders decoded to the
  one `utf-16` codec, and that codec always writes little-endian, so a
  big-endian file was quietly rewritten on a save that changed nothing else. The
  File Format window also shows the format a file actually has: a classic-Mac CR
  file used to open it reading "CRLF", so OK converted the document.

#### The four kinds of document

- **Alt+Shift+F rings through all four kinds of document** -- plain text,
  Markdown, HTML, rich text, and round again -- where it used to toggle between
  two of them. Each stop says its own name. Enter on the Format cell does the
  same. The ring was on Ctrl+Shift+M until the family keymap pass gave that
  chord to **Set Mark**, which is pressed mid-sentence and had been sitting on
  Ctrl+Alt+Shift+K; Switch Document Mode is pressed once per document and could
  afford the longer reach.

#### Headings and structure

- **A heading now says its level first**: "Heading 2, Installing" rather than
  the line followed by "Heading 2". Not a matter of taste -- a cue queued behind
  the reader is cancelled outright on a big caret jump, which is why Ctrl+Home
  onto a heading announced nothing while arrowing onto it announced it.
  **Preferences > "Say a heading's level" > After the text** restores the old
  order for anyone who prefers it.

- **Applying a heading rewrites the line** instead of stacking on it:
  Ctrl+Alt+2 on `### Notes` gives `## Notes`, never `## ### Notes`.

- **Alt+Shift+Left and Right walk HTML headings** in an HTML document, instead
  of looking for hashes it will never contain.

#### Selection and marks

- **Selections are announced the same way in QUILL Lite and QUILL.** Both now
  say the scope and the number of words --- "Selected paragraph, 41 words".
  QUILL Lite used to add a character count in front of the words and QUILL did
  not, so the same key reported the same thing two ways depending on which
  editor you were in. Words rather than characters because a word count is a
  size you can picture, where 412 characters is a number you then have to
  divide. The one selection that still says more is the **F8** span, which adds
  the lines it reached --- it is the only selection whose reach you cannot work
  out from its name.

#### Spelling

- **Suggestions spell themselves as you arrow**, and the keys that could differ
  from QUILL's no longer do. Choosing between "receive" and "recieve" by ear is
  as impossible in a list of corrections as it is in the document.

- **The spelling context menu puts the corrections first again.** Press the
  Applications key on a misspelled word and the first Down arrow lands on a
  suggestion, not on a submenu. Everything else about the word — ignore, teach,
  next and previous — is one row below them, in the same place every time. The
  submenu was the right answer to a real complaint (a menu whose length changes
  is a menu nobody can learn) and this keeps that, because the part that changes
  length is now at the top rather than in the middle.

- **F7 starts where your cursor is**, the way it does in Word, and offers to
  carry on from the beginning when it reaches the end. It used to start at the
  top of the document every time, which walked you back through everything you
  had already checked.

- **"Spell words out" now governs the F7 review too.** The switch existed and
  quietly did nothing to the one place a spelled word is most useful.

- **The spelling context menu is one submenu.** The Applications key on a
  misspelled word used to add a dozen rows to the top of the popup, which put
  Undo and Cut a different distance down the menu depending on whether the word
  under the cursor happened to be misspelled. Everything about the word is now
  under one row named after it -- *Spelling: "wrold"* -- and the first thing
  inside it is still the first suggestion. One extra press: Down, then Right.

#### The clipboard, the tray and the collector

- **A full copy tray refuses instead of overwriting slot 1.** It wrapped round,
  overwrote whatever was there and reported success -- and slot 1 holds the
  oldest thing you kept, which is the one most likely to be what you were
  saving. The refusal says both ways out.

- **Clearing the copy tray asks first, and says how many.** It counted after the
  fact; QUILL asked without a count. Each half was the one the other needed.

- **Restore Deleted Text offers the last three.** The ring has held three all
  along and the command offered one, so two were unreachable -- and the one you
  want is rarely the last thing you deleted, because the last thing you deleted
  you probably meant to.

#### Lines and text tools

- **Change Case with nothing selected changes the word you are on**, not the
  whole document -- which is what Word's Shift+F3 has always done. It matters
  more here than elsewhere: a document that has changed case reads exactly the
  same out loud, so a chord half-pressed used to be a change you could not hear.
  With a selection nothing has changed.

#### Typing, characters and the control's own keys

- **The control's own formatting chords are swallowed** in a document that
  cannot hold formatting — `Ctrl+Shift+=` and the rest applied a run to a plain
  or Markdown buffer that was never saved, and never announced. Said once per
  document, so a dead key explains itself without becoming noise.

- **An HTML document is "an HTML document".** The sentence above about a
  swallowed formatting key is built from the kind of document you are in, and
  QUILL Lite lower-cased its own Format label first --- which turned "HTML" into
  "html" and so into "a html document", while QUILL said "an HTML document" for
  the same key in the same file. The article is chosen by the *sound* of the
  label, because this sentence is spoken and an initialism is read letter by
  letter. Both editors now take the name from one shared table.

- **Curly quotes and em dashes are two switches, not one.** Preferences now has
  **Curl quotes as I type** and **Turn two hyphens into an em dash** separately,
  which is what QUILL has always had — they are different opinions and you may
  well want one without the other. Autocorrect in Customize Features is still
  the master switch, and both still start switched off.

- **Autocorrect never runs in a source or configuration file.** A curly quote in
  a `.json` and an em dash in a `.py` are syntax errors that arrive silently.
  Both editors now decide this from the kind of document rather than from a
  setting, because no setting can say "except in code".

- **A formatting refusal names the document it is refusing in**, and offers both
  ways out: rich text, or giving the document a markup language.

#### The status bar

- **The status bar stops answering for a rich document.** Encoding and Line
  Endings read "UTF-8" and "CRLF" for every `.rtf`, which has neither. They now
  say so.

- **The status bar's Format cell names all four kinds.** It said "Plain text" or
  "Rich text" and nothing else, so two thirds of the states its own Enter key
  produced were invisible in the one place somebody would check.

#### Speech, sounds, and how much it says

- **A spelling alert that asks for a tone and finds none now speaks.** On a
  machine with no sound pack it went silent, so a listener who had asked for a
  tone could not tell the alert from a clean document. A setting chooses between
  two kinds of feedback; it may never choose down to none.

#### Menus, keys and the palette

- **Three keys moved**, and each moved to the one QUILL and Word already use.
  **Set Mark is Ctrl+Shift+M** (it was Ctrl+Alt+Shift+K) -- it is a key you press
  in the middle of editing, and it was on a four-key chord while Switch Document
  Mode, which you press a few times a year, held the three-key one.
  **Switch Document Mode is Alt+Shift+F.** **Document Statistics is
  Ctrl+Shift+G**, which is Word's Word Count key.

- **A refusal that names a key reads it from your keymap.** If you rebind
  something, the sentence that tells you which key to press changes with it.

- **Page Setup moved to Ctrl+Alt+P.** It had Ctrl+Alt+U, which is Check
  for Updates in every other app in the family -- a chord that means one thing
  in eight apps and something else in the ninth is the kind of difference nobody
  finds until it does the wrong thing.

- **The menu bar is Notepad's and WordPad's again: File, Edit, View, Format,
  Navigate, Tools, Window, Help.** Eight menus where there were ten. Clipboard
  and Spelling were top-level menus of their own -- two more things to walk past
  on every Alt press, for two features neither Notepad nor WordPad puts on the
  bar at all. They are now **Edit ▸ Clipboard** and **Tools ▸ Spelling**.

- **Line work moved from Tools to Edit ▸ Lines**, which is where editing
  belongs: moving, duplicating, joining and deleting lines, sorting, reversing
  and numbering them, and removing blanks, duplicates, trailing spaces and
  stray whitespace -- all in one submenu, grouped by what they do, instead of
  spread down a Tools menu with a *More Line Work* submenu hanging off it.
  Change Case became **Tools ▸ Change Case**. **No shortcut changed**: every
  key is exactly where your fingers left it.

- **Navigate ▸ Bookmarks.** Set Bookmark 1 to 9 was nine of the fourteen rows in
  Navigate and almost none of its use, so a listener arrowing down the menu
  walked past all nine to reach anything else. They are a submenu now. Go Back
  and Go Forward moved here from Edit, to the top, where the moving-about
  commands are.

- **Format ▸ Editor Font**, moved from View, because Notepad has kept Font under
  Format since 1985 and because the editor font is not a rich-text feature. It
  is the one row the Format menu keeps if you switch rich text off -- which
  leaves you with Notepad's Format menu, exactly.

- **Preferences and Customize Features moved to Tools**, where Windows
  applications have kept their settings since Word 6.

#### Sharing with QUILL

- **One shared set of abbreviations, a dictionary and more (2026-09-18).**
  QUILL Lite already pointed at QUILL's abbreviations and personal dictionary
  when you asked it to. QUILL now has the other half: **Tools ▸ Customize and
  Support ▸ Bring My QUILL Lite Settings...** merges your QUILL Lite
  abbreviations, dictionary, copy tray, clip library and bookmarks into QUILL,
  turns those switches on for you, and copies your preferences and rebound keys
  across once. Nothing already in QUILL is replaced and nothing here is removed.

- **A shared dictionary is actually shared.** With **Use QUILL's dictionary**
  on, a word taught in QUILL is known here immediately — it used to take a
  restart. And two apps teaching a word at the same moment no longer lose one of
  them.

#### Speed

- **Large documents stopped costing what they did.** QUILL Lite read its whole
  buffer out of the text control five separate times -- the status bar's counts,
  the heading cue, the list cue, the live spell check on every arrow press, and
  the autocorrect rule on every single keystroke. In a big file that is what made
  arrowing feel heavy. It reads once per edit now and answers everything else
  from what it already has, and the autocorrect rule asks for one character
  instead of the document. Nothing looks different; a long file simply behaves
  like a short one.

#### Downloads, updates and packaging

- **Two downloads, not four.** QUILL Lite publishes an installer and a portable
  zip. The thin `QuillLite-Lite-Setup` and the launcher-only
  `QuillLite-Companion` zip are retired, and neither was right for this
  product: the Companion zip installs nothing, so it ran against whatever
  shared runtime happened to be on the machine -- including one built before
  QUILL Lite existed, which failed at launch with "No module named
  quill.apps.lite" and could not repair itself. The thin installer swapped a
  117 MB download for a 110 MB first-launch download and a network dependency,
  on the one app people install *because* they have nothing else. If you
  already installed the thin edition, the installer upgrades it in place --
  same AppId, nothing to uninstall -- and Check for Updates offers it to you.
  The other QuillVille apps are unchanged.

#### Documentation and QA

- **The guide covers all of it**: the File Encoding and Line Endings window
  including its **keep as is** rows, what the Encoding and Line Endings parts of
  the status bar say in a rich text document, and the formatting keys the editing
  control brings with it. The sign-off checklist gained **Block R** (L-223 to
  L-236) for this release's additions, and L-226 --- the rich-document status
  cells --- joined the fifteen-minute pass.

### Fixed

#### Files, encoding and saving

- **Save As converts the file, not the window.** Saving a rich text document as
  plain text, or an HTML one as Markdown, used to change the document in front
  of you *first* and then try to write it. If the write failed — a locked file,
  a full disk — you were left holding flattened text under the old name, with
  the next Ctrl+S ready to write it over the original, and the formatting gone
  from the window as well because that change could not be undone. The file is
  written first now, and the window follows only when the write succeeded.

- **A character the file cannot hold is a question, not a silent loss.** Typing
  an em dash or an emoji into a file stored in an older encoding used to turn it
  into a question mark, with "Saved" announced as though nothing had happened.
  QUILL Lite now asks before it writes: save as UTF-8 and keep everything, save
  as asked and lose them knowingly, or cancel.

- **Earlier Versions says what a rich restore costs.** A backup is a copy of the
  text, not the formatting, so putting one back into a rich text document keeps
  the words and loses the styling. The dialog offered the rows and said nothing.

- **File Encoding and Line Endings is no longer offered in rich text.** It let
  you choose, dirtied the document and announced a change that never happened: a
  rich text file has its own format and neither setting is read when it is
  written.

- **Markdown is gone from the Save As type list.** A type in a Save As box is a
  promise about what will be written, and there is no Markdown writer: picking
  it saved the same plain text under a different extension. Opening a `.md` is
  unchanged.

#### The four kinds of document

- **Switching out of rich text keeps your work.** It used to take the letters
  and leave everything else: an afternoon of headings and bold became a wall of
  unmarked text, announced as "Plain text mode", with no undo. Both directions
  convert now. Out of rich text, a Heading 2 becomes `## `, a bold word becomes
  `**bold**` and a bullet list becomes `- ` lines — and the document is then a
  Markdown document, so heading navigation and the headings list still find
  everything. Into rich text, a Markdown document's `## Title` becomes a real
  heading instead of sitting there as two hash marks. Anything the target cannot
  carry — a table, a picture, a footnote — is named before you are asked.

- **A document that changes mode keeps its name.** It used to forget it, so
  Ctrl+S asked you to find your own file again with nothing filled in. The name
  is kept, and Save offers the right suffix for what the document now holds —
  `notes.rtf` for a `notes.txt` you made rich. Nothing is ever written under a
  name that does not match what is in it.

#### Headings and structure

- **Moving a section works in an HTML document.** Alt+Shift+Up and Down were
  looking for Markdown hashes whatever the document was, so in a `.html` they
  said there was no section where there plainly was one.

- **Announce Headings is remembered between launches in QUILL too.** It never
  was: QUILL wrote the setting and never read it back. QUILL Lite was never
  affected -- its loader walks the dataclass fields rather than naming each one
  -- but the two products share the switch, so it is fixed here as well.

- **Ctrl+Home onto a heading announces it.** See the heading-order change above.

- **Heading 5 and Heading 6 could be applied and never found again.** Both sat
  at the 11-point body size, so the ladder could not tell either from an
  ordinary paragraph: heading navigation and the headings list walked straight
  past them. They have sizes of their own now (11.5 and 10.5), which is what
  made it honest to offer all six in **Format ▸ Headings**, each on its own
  digit — Alt+O, H, 3 and Ctrl+Alt+3 are the same three.

#### Selection and marks

- **Go to the Start of the Selection now goes there.** `Alt+Shift+F8`
  announced that it had arrived and left the cursor at the far end, because the
  call that selected the text put the cursor back where it started from. It
  lands at the beginning now, with the selection intact.

- **Marks survive editing.** A mark used to be a bare position, so inserting a
  paragraph above one left it pointing at whatever had since moved into that
  spot. Each mark now remembers the text around it and finds that text again ---
  the same way numbered bookmarks have worked since the last release.

- **Reselect knows about every way of selecting.** `Ctrl+Shift+F8` only
  remembered selections made with **F8**, Select Sentence and Select Block ---
  so Select Word, Select Line, Select Paragraph, Expand and Shrink, the ones
  people actually reach for, were the ones it could not put back.

- **The mark ring holds twenty and never holds the same place twice.**
  QUILL Lite kept its own list of ten beside the shared ring; there is one ring
  now, and it is the shared one.

#### Navigating, bookmarks and going back

- **Alt+Left comes back from a mark.** Pop Mark, the mark list and Exchange
  Point and Mark moved the cursor without telling the Back key, so those were
  the three jumps `Alt+Left` could not undo. A Back key that skips some of the
  places you have been is worse than no Back key.

- **A bookmark now finds its own text again after an edit.** Bookmarks were
  moved by a guess -- the document's length changed by so much and the cursor is
  here, so everything after it moves -- which is right for one insertion and
  wrong for a Replace All, an undo, a paste over a selection, or a reload. A
  bookmark now remembers the words around it and is re-found from them, which is
  how QUILL's named bookmarks have always worked. Bookmarks you already have
  keep working; they gain the new behaviour the next time you set them.

#### Finding and replacing

- **All Matches selects the match you chose.** It selected however many
  characters the *first* match had, which for a search that finds runs of
  different lengths meant the selection ended somewhere you did not ask for.

- **Ampersands showed in the Find and Replace search-mode boxes.** The three
  rows read "&Normal", "&Escapes" and "Re&gular expression" on screen and out
  loud. An ampersand is an access key in a button or a menu item and a literal
  character in a list row, and these were list rows. They are also better named
  now: "Normal text", "Special characters (	, 
)" and "Regular expression",
  because "Escapes" names the mechanism rather than the job.

- **All Matches and Count Occurrences refused instead of asking.** With nothing
  searched for yet they said "Search for something first", which is true and a
  dead end. They open Find now.

#### Spelling

- **F7 skips the words you have told it to ignore.** Every other route honoured
  them -- the check as you type, Ctrl+F7, the right-click menu -- and the full
  review did not, so a word you had deliberately skipped was the first thing it
  stopped on.

- **"No further misspellings" now says how many are the other way.** On its own
  it reads as "your document is clean", which is a lie when seven are sitting
  behind the cursor -- and it did not say that pressing the other key would find
  them. QUILL has counted the other direction for years.

- **F7 on an empty document says so** instead of doing nothing at all, which is
  indistinguishable from a key that is not bound.

- **Spelling for This Word (Shift+F7) and Add Word to Dictionary (Alt+F7) work
  from anywhere in the word.** They used to answer only when the caret was on
  its first character, and said "No misspelling at the cursor" everywhere else.

- **Spell check as you type had never once fired.** It asked for a word
  beginning exactly at the cursor, which typing left to right never produces --
  the cursor is always at or past the end of the word you just finished. The
  status line, the file-type exemptions and the setting all existed and none of
  them had ever run.

- **Ordinals are no longer misspellings.** "the 13th of May" reported "th" as a
  misspelling, at a position inside a number, for a word you never typed. The
  same fix covers 3D, 1080p, 500ml and 12pt.

#### The clipboard, the tray and the collector

- **The empty copy tray named the wrong key.** "Control Shift 0 copies into it"
  was a chord that had not been Copy to Tray since before 1.0, and could not be
  right anyway once the key was rebindable. It now reads whatever Copy to Tray
  actually answers to.

- **The collector's count no longer counts dashes.** Collecting a piece with a
  line of `----` in it -- which is most log files -- inflated "Collected N
  pieces". The pieces are counted now rather than inferred from the text.

- **Clearing an empty collector says so**, instead of reporting "Collector
  cleared" whether it discarded five gathered quotes or nothing at all. When it
  did discard something it now says how much.

#### Typing, characters and the control's own keys

- **Describe Formatting (Ctrl+Shift+D) reads Markdown.** With the cursor inside
  `**bold**` or on a `## heading` it said "Plain text", which is not a
  description of the formatting but a denial that there is any. It now reads the
  markup the way QUILL does.

#### The status bar

- **F6 now leaves the status bar as well as entering it.** Escape still works;
  so does the key that got you there. Shift+F6 too.

#### Speech, sounds, and how much it says

- **A screen reader read the line above the cursor on every empty line.** Type a
  line, press Enter, and ask JAWS to read the current line: it said the line you
  had just finished instead of "blank". Not a speech bug and not a JAWS bug --
  the control was answering the question wrongly. QUILL Lite put the Rich Edit
  into its own plain-text mode (`EM_SETTEXTMODE` / `TM_PLAINTEXT`), and in that
  mode RICHEDIT50W does not count the position after a trailing line break as a
  line of its own: asked which line the caret was on, it named the previous one,
  and a screen reader read out what it was told. The control now stays in
  rich-text mode whatever the document is, and the plain/rich distinction lives
  where it belongs -- in the document, deciding what the Format menu allows and
  what a save writes. One consequence, deliberately: **pasting into a plain text
  document is always a plain paste**, because a plain document must not pick up
  formatting it would silently drop at the next save.

- **"Entered Preferences dialog" / "Exited Preferences dialog".** QUILL Lite no
  longer speaks either, for any dialog. A screen reader announces a dialog by
  its title when it opens and says where focus lands when it closes; saying it
  again is the app talking over the reader.

#### Printing

- **Page Setup is remembered.** Paper size, orientation and all four margins
  went back to the defaults at every launch, so anybody not printing A4 with
  15 mm margins set them again every session.

#### Windows, sessions and recovering unsaved work

- **Crash recovery puts your file back the way it was.** The copy kept aside is
  always written in one format, because it has to hold whatever you typed — and
  the recovered document used to adopt *that* format, so a file in an older
  encoding, or one with Unix line endings, came back changed and was saved that
  way. What the copy records now is what your document was, and the restore puts
  it back.

- **A recovery that fails claims nothing.** If the copy could not be read,
  QUILL Lite still took your file's name, marked the empty window as changed and
  set the copy as its own — so closing that window and answering "No" deleted
  the only copy of the work. It now says the recovery failed, takes nothing, and
  leaves the copy for next time.

#### Menus, keys and the palette

- **The Keyboard Manager refuses a key Windows will not send.** Some chords look
  fine, save fine, and then never fire -- the menu advertises a key that does
  nothing. The check existed and ran only from the Audit button, after the
  damage; it now runs when you assign.

- **The menu bar had a "Document" item before File, and two menus called
  Window.** Both came from the MDI machinery rather than from QUILL Lite.
  Windows adds a maximised child's system menu to the menu bar as an untitled
  icon, which a screen reader announces as "Document", so pressing Alt landed
  on "Document" instead of File; and wxWidgets builds a *Window* menu of its own
  (Cascade, Tile, Arrange Icons) and inserted it beside the one QUILL Lite
  builds, so the bar said "Window" twice with no way to tell which was which.
  The system menu is gone -- along with the three unnamed minimise, restore and
  close icons at the other end -- and wx's Window menu with it. QUILL Lite's own
  Window menu, the one that lists your documents by number, is the one that
  stayed.

#### Features, profiles and preferences

- **Customize Features no longer promises sentence capitals.** Autocorrect does
  curly quotes and em dashes; it has never capitalised a sentence, and saying
  otherwise sent people looking for a switch that was not broken.

- **Choosing a profile in Customize Features now applies it.** It used to need a
  second press of a **Use Profile** button that nothing mentioned, so choosing
  Notepad and pressing Save kept every feature you had -- and the Format menu the
  description had just promised would be gone. Choosing applies; Custom puts the
  boxes back to how you found them; nothing is saved until Save.

- **Each profile now shows what it would do**, computed from the feature list so
  it cannot go stale, in a read-only box a screen reader can arrow through
  rather than a caption it can only read all at once.

- **Page Setup and Customize Features did nothing.** Two menu items that opened
  no window and said nothing: Page Setup used `with` on the one wx dialog that
  is not a context manager, and Customize Features called a method by a name it
  does not have. Both failed inside the menu handler, where wx swallows the
  error, so there was nothing to see.

- **The Preferences font button said only "Choose".** A button is announced on
  its own, so "Choose button" named no noun and the only way to find out what it
  chose was to press it. It is "Change Font..." now. Two access keys in that
  window were also claimed twice, so one of each pair could not be pressed.

- **Format ▸ Structure survived rich text being switched off**, offering to
  promote and demote headings in a plain text document that cannot have any.

#### Downloads, updates and packaging

- **The portable copy stopped leaving itself on the host machine.** A portable
  QUILL Lite wrote its settings, recent files and -- worse -- its *recovery
  copies of unsaved documents* into `%LOCALAPPDATA%\QuillLite` on whatever
  computer it was plugged into, instead of into the `data` folder on the stick.
  Nothing said so, and the bundle even shipped a file asking for portable mode
  that was never read, because a bundle has to be recognised as portable before
  that file can be found -- and `QuillLite.exe` was missing from the list of
  names that counts as recognition. Inkwell, Beacon, Social and Cast were
  missing from it too. If you have been carrying a portable QUILL Lite, that
  folder is where anything you seem to have lost will be, and it is worth
  deleting once you have what you want out of it.

#### Documentation and QA

- **The guide's Title Case key was out of date.** It is Ctrl+Shift+T;
  Ctrl+Shift+G is Document Statistics, which is Word's Word Count key.

- **The spelling keys in this guide were two versions out of date.** Suggestions
  for a word is Alt+Shift+F7 and Add to Dictionary is Ctrl+Alt+F9; the guide
  still said Shift+F7 and Alt+F7.

#### Reliability

- **Two timers could fire on a window that had been closed.** The live spell
  check and the pending "and here is how it is spelled" were left running when a
  document window went away, and the failure that followed was swallowed. Both
  are stopped now, with everything else on a clock.

#### Formatting that did not survive being converted (2026-09-24)

- **Underline reached rich text as four literal characters.** Markdown has no
  underline syntax, so the tag picker writes `<u>text</u>` -- and the rich-text
  writer only understood QUILL's own span spelling, so switching a Markdown
  document to rich text put `<u>` on the page beside the words it was supposed
  to be formatting. The two spellings are one now, and `~~strikethrough~~` came
  with it.

- **Page breaks vanished.** A `::: pagebreak` written to rich text was not read
  back, so a document that paginated correctly stopped doing so after a save and
  reopen, silently.

- **Tables came back as one word.** Converting through HTML turned `| a | b |`
  into `ab` -- the header, the columns and the alignment row all gone. A table is
  the one construct where losing the markup also loses the meaning, because
  nothing else says which value sits under which heading.

- **Fonts, colours, sizes and super/subscripts** were dropped by the same route,
  arriving as bare words. So were alignment, line spacing, indents and named
  styles.

- **Converting to plain text left the markup in.** `<u>` and `~~` came through
  intact into a file whose whole promise is that it contains no markup.

Twenty-eight constructs now survive both round trips exactly, asserted one by one
in `tests/unit/io/test_format_fidelity.py`.

- **Alt+Shift+F still converts nothing.** The ring walks plain, Markdown, HTML
  and rich, and the first three stops change what the *keys* write rather than
  what the buffer holds. That is deliberate: converting at each stop would
  rewrite the document three times on the way to the one you wanted, and wrap a
  plain note in a full HTML page for the crime of passing through. Rich text is
  the stop that costs something, and it is the one that asks first.

#### Headings (2026-09-24)

- **The cursor landed outside the heading.** Applying a heading in an HTML
  document put the cursor *inside* `</h1>` -- QUILL Lite's own arithmetic added
  the whole length change to the caret, counting the closing tag as though it
  were in front of it. On an empty line it landed after the tag entirely. Both
  editors now take the answer from one place.

- **A heading on an empty Markdown line was not a heading.** `Ctrl+Alt+1` wrote
  `#` without its trailing space, so what you typed became `#Heading`, which no
  Markdown parser reads as a heading. The reader says nothing, the outline stays
  empty, and it only shows up in the published document.

#### Rich text that other programs read (2026-09-24)

- **Quote, Title, Subtitle and Caption were written as nothing at all.** The
  rich-text writer handled alignment, spacing and indent and dropped the named
  style on the floor. They are real styles now, declared under the names Word
  knows them by, so a file you send opens in Word as Quote rather than as text
  that happens to be indented and italic.

#### The documents, and what they were teaching (2026-09-24)

- **The key list stopped printing "Tools" twice.** The generated table in the
  user guide started a new heading every time the menu path changed, and the
  Tools menu's rows are interrupted by the Spelling submenu and then resume --
  so five rows, Quiet Mode and Sound Scheme among them, were stranded under a
  second table with the same name. Somebody hunting Quiet Mode found the first
  table, did not find it, and had no reason to suppose there was another.

- **The six second keys are in the guide now.** `Ctrl+;`, `Ctrl+'`, `Alt+F7`,
  `F12`, `Ctrl+F12` and `Ctrl+Shift+F12` are real bindings that appear in no
  menu label, so a table built from the menu rows told you your whole keyboard
  and left six working keys out of it.

- **Autocorrect never capitalised a sentence.** Three places said it did -- the
  Everything profile's description, the typing module's own docstring, and the
  user guide -- and the code has only ever had two rules, curly quotes and em
  dashes. Somebody switches the area on to get the capitals and concludes the
  app is broken. The guide also now says the part that actually bites: the area
  is a master switch, and **both rules start switched off** in Preferences, so
  turning the area on alone changes nothing.

- **Six stale chords in the documents.** Back Up Settings and Restore Settings
  were written as `Ctrl+Alt+Shift+Q` and `Ctrl+Alt+Shift+D` (they are
  `Ctrl+Alt+F11` and `Ctrl+Alt+F12`), Customize Features as `Ctrl+Alt+Shift+F`
  (`Ctrl+Alt+F10`), the Heading Organizer as `Ctrl+Alt+Shift+O` (`Alt+Shift+O`,
  and that spelling is Sound Scheme), Snippets as `Ctrl+Shift+Insert`
  (`Alt+Shift+I`), and Spelling for This Word as `Shift+F7` (`Alt+Shift+F7`).
  Every one of those chords is bound to *something*, which is why the gate that
  catches keys nothing binds did not catch these: following the guide did the
  wrong thing rather than nothing.

  **A gate for it now** (`tests/unit/docs/test_documented_chord_ownership.py`).
  A document states a checkable claim every time it writes a command's name
  beside a chord, and the command table is the authority for what that chord
  should be. Six documents are read, the PRD among them -- the older gate
  leaves PRDs out because they quote rejected proposals, and that is the right
  call for "does anything bind this" and the wrong one for "does *this
  command* bind it".

- **The Insert menu is not inside Edit.** Two passages still routed people
  through `Edit ▸ Insert ▸ ...` for Special Character and Line Break, from
  before Insert became a menu of its own.

- **Nine lessons, not eight**, said in four places -- and the test that guards
  the tutorial window was still asserting eight, so the ninth lesson (asking a
  question about a document) shipped uncounted.

- **A duplicated section in the user guide.** "Links" appeared twice, in full,
  one after the other; and "Making QUILL Lite smaller (or larger)" was a heading
  with nothing under it, because the section that belonged to it sat inside
  "Sounds" four screens below. A listener arrowing by heading reached the title,
  heard the next heading immediately, and concluded the section was empty.

- **A status bar cell that does not exist.** The guide's table carried a
  **Language** row as well as **Format**: the one cell had been split in two in
  an earlier draft and never rejoined, so the table described fourteen cells
  where the bar has thirteen. Somebody arrowing along the bar counted wrong and
  then went hunting for a cell that has never existed, which is the same dead
  end as a key that does nothing. `test_lite_docs.py` checked that every real
  cell is named and nothing checked the other direction; it does now, row count
  included. The README's "ten focusable cells" was wrong by three as well.

- **Numbers that had drifted.** The special-character picker was advertised at
  "1,400" and holds 357 in 15 groups; the HTML picker at "forty tags" and offers
  111 plus 20 whole form fields; the autosave interval's default was written as
  60 seconds and is 30; the QA sign-off was cited as 80 steps and has 254; and
  the feature areas were counted as seventeen in four places after AI help made
  them nineteen.

- **The theme default, in four documents.** They all said dark; it has been
  `system` since the reasoning above was written down.

- **"If you want artificial intelligence, that is QUILL."** True until
  2026-09-23 and printed in the guide that ships with the release that added
  it.

- **Two profiles under-reported what they take away.** WordPad and Notepad each
  switch off **AI help** and **Markdown and HTML**, and neither section listed
  either: Notepad's paragraph named fifteen of its seventeen removals. What a
  profile keeps is visible the moment you use it; what it removes is a menu that
  is not there, which is exactly what somebody does not notice and cannot look
  up. Somebody choosing Notepad for a small editor and then finding Ctrl+B in a
  `.md` no longer writes asterisks had no way to connect the two. `test_lite_docs`
  now asserts every removal is named in its own section, and that a **new area**
  cannot be added without giving the check a phrase to look for.

- **Go To Anything had no section**, only a row in the feature table, so the one
  box that searches commands, headings and bookmarks together was a thing you
  could switch on and then not know what to press. It has its key
  (**Ctrl+Alt+Shift+A**), its section, and the reason it ships off.

- **A contents list at the top of the user guide.** Thirty-seven sections and no
  way to see the shape of it except by walking the headings. Generated from the
  guide's own H2s, so it cannot drift.

#### Reported while testing (2026-09-21 to 2026-09-22)

- **The status bar answers Insert+Page Down.** JAWS's read-the-status-bar
  command returned "CRLF (Windows) Modified" and nothing else. That command does
  not look for a role; it looks for a window of a particular class and reads its
  parts, and finding none it scrapes the bottom line -- which, on a wrapping
  panel, was the last two cells of twelve. There is a real status bar window
  behind the accessible one now, carrying the same cells as parts.

- **Document numbers never came back.** The counter only counted up. That number
  is the handle -- Alt+1 to Alt+9 reach the first nine and the Window menu is
  written in them -- so after opening and closing ten documents in a morning the
  eleventh had no Alt+digit at all, while ten working numbers belonged to
  nothing. It takes the lowest free number now, open documents are never
  renumbered, and the Window menu lists in number order.

- **The status bar read back as halves and doubles** -- "Line 1, colu Line 1, c
  ... No selectio" -- because the cells were *moving*. "No selection" to "1
  words, 8 characters selected" is ninety pixels, and it shoved the nine cells
  after it sideways on every selection change. The cells hold their width now.

- **Enter in Find did nothing.** You typed a word, pressed Enter, and had to Tab
  to the Next button. The code set an affirmative id, which says which button
  means yes *when a modal dialog closes* -- and Find is modeless, so it never did
  anything. Enter and Shift+Enter are handled outright now, and Find Next is a
  real default button. Replace answers Enter with **Find Next**, never Replace,
  which is what the Windows Replace dialog does and the safe answer either way.

- **QUILL stopped crashing.** An access violation inside the subclass that gives
  a screen reader the corrected caret line took the whole process down. It is
  unwound safely now: a fault there costs a line number, not your document.

### Fixed in QUILL, for every QUILL user

Both were isolated in PR #1490 and left unapplied so that adding an app and
changing the editor stayed separate decisions. Both decisions were taken.

- **`_TOM_TRUE` was `tomUndefined`, so every rich-mode heading lost its bold.**
  `tom.h` defines `tomTrue` as `-1`; QUILL used `-9999999`, which the same
  header defines as `tomUndefined` -- "leave this property alone". Assigning it
  to `ITextFont.Bold` asked the control to change nothing and *succeeded*, so
  `set_heading` applied the point size, silently never applied the bold, and
  raised nothing. Because `heading_level_for_font` requires bold before it will
  call a paragraph a heading, QUILL could not then find the headings QUILL had
  just made: heading navigation and Describe Formatting both went blind.
  Measured on RICHEDIT50W / Riched20 10.0.26100 -- `Bold = -9999999` gives
  `Weight=400`, `Bold = -1` gives `Weight=700`. Reproduced standalone in
  `tests/repro_tom_true.py`, which imports neither QUILL nor QUILL Lite.

- **A collapsed cursor described the paragraph above it.** A collapsed range in
  the Text Object Model reports the formatting of the character *before* it, so
  standing at the head of a heading and asking "what is this?" answered with the
  body text above. `caret_format_description` now probes the character after the
  cursor, which is what a screen reader describes.

### Added in QUILL, so the editor is never behind its own small sibling

- **Justify**, completing the four alignments -- the Rich Edit surface has
  always supported it and nothing was bound to it. It landed on Ctrl+Alt+J and
  is **Ctrl+J** now, WordPad's key and QUILL Lite's; see the note at the end.

- **Line spacing** -- single, one-and-a-half and double (Ctrl+1, Ctrl+5, Ctrl+2).

- **Grow and Shrink Font** (Ctrl+Shift+> and Ctrl+Shift+<), stepping a ladder of
  real point sizes that includes the heading sizes, so growing a heading stays
  on the heading ladder rather than falling off it.

- **Paste Text Only**, which neither product had. It landed on Ctrl+Alt+V and is
  **Ctrl+Shift+V** now, in both editors; see the note at the end.

- **Bullets in rich mode**, driving the real list type instead of inserting a
  Markdown dash into a Rich Text document.

- **`edit.select_word` (Ctrl+Alt+W)**, which did not exist. QUILL could select a
  line, a paragraph and a block, and the innermost rung of its own expansion
  ladder was the one thing it could not be asked for directly.

- **A key for `edit.select_line` (Ctrl+Alt+E)**, which was registered, was in the
  Edit menu, and was in no keymap at all -- so its label advertised no shortcut.

- **Keys for three commands that had none**: `edit.select_paragraph`
  (Ctrl+Alt+Shift+P, unbound since Ctrl+Alt+P was dropped under §10.8, which the
  authored Ctrl+Alt set reverses), `edit.duplicate_selection` (Ctrl+Alt+Shift+Q;
  §4.17 avoided Ctrl+D, not the command) and
  `edit.toggle_extend_selection_mode` (Ctrl+Alt+F8, previously reachable only by
  opening the keymap editor to assign one).

- **`quill.core.selection.shrink_selection`**, a computed inverse of
  `expand_selection`, and `MainFrame.shrink_selection` now falls back to it when
  there is no expansion history. The stack only knew about selections reached
  *by expanding*: selecting a paragraph outright and asking to shrink said "no
  selection to shrink", which a listener cannot tell apart from a broken
  command.

- **A live spell check that stays quiet in code** (`spellcheck_skip_code_files`,
  on by default). `spellcheck_live` already suppressed URLs, code spans and
  fenced blocks, which is the right granularity *inside* prose and no help
  whatever in `main.py`, where the whole file is the exception. QUILL now
  consults the shared file-type rule before every live alert. The F7 review is
  deliberately not gated: a default decides what happens when nobody has said
  anything, and running the review is saying something.

- **`load_combined_dictionary` and friends take a `personal_dir`**, so a sibling
  app can keep its own taught words in its own folder instead of growing a
  `%APPDATA%\Quill` on a machine that has never had QUILL installed. QUILL
  passes nothing and gets exactly what it got before.

- Every QUILL editor tab is now built on the extended surface, so all of the
  above is available by construction rather than through a second code path.

### A note on the two keys that used to differ

QUILL Lite shipped using WordPad's `Ctrl+J` for Justify and `Ctrl+Shift+V` for
Paste Text Only, where QUILL had spent both keys long before -- `Ctrl+J` on Set
Temporary Bookmark and `Ctrl+Shift+V` on Preview -- so the two products disagreed
about two keys and the reason was recorded in the keymap.

The family parity pass closed it the other way round: **QUILL moved its own
commands** and both keys now mean the same thing in both editors. An existing
binding somebody's hands already know does outrank a new command's convention,
which is why this took a deliberate decision rather than a patch -- but two
editors in one family disagreeing about Justify outranks both. `Ctrl+Alt+J` and
`Ctrl+Alt+V` are Set Temporary Bookmark and the copy tray in QUILL now; the eight
keys that still differ on purpose are listed in `quill/core/lite/parity.py`, each
with its reason.
