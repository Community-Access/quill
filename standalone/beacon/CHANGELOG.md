# Changelog

## 0.1.0 - 2026-07-15

The current build is **0.1.0 (build 2)**. Build 2 keeps the first slice of
2026-07-15 (below, under "The first slice") and adds everything in the next
sections.

### Since build 2 (2026-10-27 to 2026-10-31)

- **Shared-runtime licensing.** Installed editions use the QuillVille Runtime,
  which currently carries PyMuPDF 1.28.2 under AGPL-3.0 through the shared
  GLOW dependency; Beacon does not itself expose GLOW. Release-specific source
  and legal review are required before the next public release. Portable
  contents must be checked separately. See Licences and Notices and the
  PyMuPDF distribution review.
- **Windows Media closes cleanly after an audio device change** (2026-10-27).
  The shared player no longer keeps Windows audio-device objects in a cache and
  removes its event handlers when it stops. This fixes a crash on exit after the
  output device was listed or switched; choosing a device and playing work as
  before.
- **Controls that had no label now have a spoken name** (2026-10-30).
  JAWS, NVDA and Narrator used to announce them as a bare role, such as
  "edit" or "list". Now they say what they are: the bookmark search box, sort order and
  results, the command filter and list, a trail's steps and the note for a
  step, the status report, Preferences sections, Smart Collections,
  Attachments, the folder path, and the sign-in link or token box.
- **Sharp text at any display scaling** (2026-10-31). QuillBeacon now handles
  each monitor's scaling itself instead of letting Windows stretch it, so
  text stays sharp at 125, 150 and 200 percent and on monitors with
  different scaling, and windows and list columns keep their proportions.
  Setting the environment variable `QUILL_DPI_UNAWARE` to `1` turns this off,
  for diagnosing a display problem (#1702).
- **Pygments in the notices** (2026-10-31). The shared runtime now bundles
  Pygments, which QUILL and QUILL Lite use to read code and web pages for
  spell check, so QuillBeacon's third-party notices list it.

### Keys, menus and the guide

- **Every menu command has a key, and every command has its own letter**
  (2026-10-17). Sixteen commands on QuillBeacon's menus could only be reached
  by walking the menus. Each now shows a key beside its name:
  **Edit > Find Duplicates** (Ctrl+Alt+D),
  **View > Accessibility Settings...** (Ctrl+Shift+Comma),
  **Media > Play in External Player** (Ctrl+Alt+P),
  **Media > Add Radio Station...** (Ctrl+Alt+R),
  **Media > Add Radio Program...** (Ctrl+Alt+G),
  **Tools > Trail Editor...** (Ctrl+Alt+T),
  **Tools > Smart Collections Manager...** (Ctrl+Alt+Shift+G),
  **Tools > Revalidate Health...** (Ctrl+Alt+H),
  **Tools > Review Location Repair...** (Ctrl+Alt+Shift+H),
  **Tools > External Player...** (Ctrl+Alt+Shift+X),
  **Tools > Status Center...** (Ctrl+Alt+I) and **Help > About** (Alt+F1).
  The Sync menu lives on F9: **Sync > Sync Now** (F9),
  **Sync > Sync Settings...** (Ctrl+F9), **Sync > Sync History...** (Shift+F9)
  and **Sync > Auto Sync...** (Ctrl+Shift+F9). The Command Palette shows the
  same keys.

  Two commands had no access letter at all (**Edit > Archive** and
  **Tools > Publish Collection...**), and nine letters were shared by two to
  four commands in one menu, so pressing the letter only moved between them.
  Every command now has a letter of its own in its menu; Archive is H,
  Publish Collection is L, Find Duplicates is P, and the guide lists every
  letter that moved. For example, Alt+S, then N syncs now, and Alt+E, then P
  finds duplicates. The keys cannot be changed yet, and they work in the main
  window rather than inside dialogs. The menu check that runs during testing
  now walks QuillBeacon's real menu bar too, and fails on any command without
  a key, any key shown twice, any key Windows cannot bind, and any letter two
  commands share. See **Every menu command has a key** in the guide.
- **The guide names real menus, and a check keeps it that way** (2026-10-17).
  The QuillSync and QuillBeacon guide described where commands live in prose
  ("Tools, then Publish Collection") that nothing could check. Every such
  place now gives the menu path and key exactly as the menu bar shows it, for
  example **Tools > Publish Collection...** (Ctrl+Shift+W) or
  **Sync > Sync Settings...**, and a new section, **Keys and menus you will
  use most**, covers searching (**View > Search**, Ctrl+F), saving, opening,
  trashing and undoing, Where Am I (Ctrl+F1), Next Pane (F6) and the Command
  Palette (Ctrl+Shift+P), with a worked example that saves a search as a Smart
  Collection. At first it listed the commands that had no key, such as
  **Edit > Find Duplicates** and the Sync menu; those keys arrived the same
  day (above), and the guide now teaches them.
  The 0.1.0 entry below that gave Where Am I as F1 now says it moved to
  Ctrl+F1. A check now builds QuillBeacon's real menus during testing and
  fails if this changelog or the guide names a menu path or key the menus do
  not have, or if two menu rows show the same key. Its first run found
  nothing the menus lacked; the prose paths it could not read were the gap.

### Speech, sound and safe keyboard use

- QuillBeacon now speaks (#1283, #1300). Every announcement went to the
  status bar (or, failing that, the window title) and nowhere else, and
  screen readers announce neither on their own -- so "QuillBeacon ready",
  result counts, filter changes and undo confirmations were silent.
  Announcements now also go through the shared announcement service, which
  speaks them through your screen reader and writes them to a connected
  braille display. The status bar still updates as the visual floor, and
  every existing announcement call site gained speech without changing.
- **Where Quill Beacon's own sounds play, and Alt+Shift+M to turn them off.** **Tools > App Sounds Play On...** (Ctrl+Alt+S) offers System default, None (no sounds), or any sound card or headset by name. After a change one sound plays on the new card, so you hear where it went. If that card is unplugged the sounds play on the system default until it is back, and Quill Beacon says so once. **Alt+Shift+M** turns Quill Beacon's sounds off and back on where they were, and **Tools > App Sounds** shows a check mark while they are on. Each QUILL app keeps its own choice; "Share these choices with my other Quill apps" keeps them in step. Your screen reader is never moved. Asked for on QUILLVille by Rick Lewis.
- Destructive confirmations default to No: permanently deleting selected
  items, deleting a smart collection, and removing an attachment all open
  their Yes/No prompt with No preselected, so a stray Enter or Space
  cannot destroy anything.
- Every dialog answers Escape and Enter (WCAG 2.1.2). Twenty dialogs plus
  the command palette were built without the shared modal-id contract, so
  Escape and Enter were not mapped to their own Cancel/OK/Close buttons --
  a keyboard trap. All of them now wire the contract, using only ids that
  a real button backs.

### Help

- **Help > What's New** (Ctrl+Shift+F1) opens this changelog in your browser,
  on the same key as every other QuillVille app.

### Saving and finding places

- Capture routing rules (PRD 14.5, 44.11): an ordered keyword -> folder list
  files new web bookmarks automatically. First matching rule wins; each
  keyword can be used by only one rule. Applied at every web capture surface
  (extension bridge, native messaging, quick capture, CLI, imports) unless
  the user explicitly chose a folder; routed bookmarks still land in the
  Inbox. Edited under Preferences > Routing Rules with keyboard-only
  reordering.
- Location resolution gained a final fallback layer (PRD 10.2): after the
  built-in native / structural / text-quote / fuzzy / positional locators
  all fail, an extension-contributed `beacon.resolver` may place the
  location, always at a needs-review confidence so it can never silently
  replace an exact bookmark. A sample resolver extension ships with QUILL.
  This is groundwork: QuillBeacon does not host extensions yet, so the
  layer has nothing to consult on a stock install.

### Media

- The built-in media player runs on the family's shared audio layer, so it
  inherits the default wx.media backend plus the opt-in libmpv backend
  (gapless playback, exact seeking, output-device routing). With no
  backend available at all it announces "media backend unavailable"
  instead of failing.

### Safety

- Outbound-URL safety for anything the user (or an imported OPML file)
  supplies: feed fetches and link-health checks now refuse non-http(s)
  schemes and hosts that resolve to private, loopback, or link-local
  addresses, and cap the response body, so a pasted URL cannot be used to
  reach the local network or stream unbounded data into memory.

### Downloads, packaging and updating

- **Two downloads, nothing else** (2026-10-11). QuillBeacon now comes as the
  installer and the portable zip. The small Lite installer and the Companion
  zip are gone. If you used the Lite installer, take the installer; if you
  used the Companion zip, take the portable zip. Check for Updates already
  offers the right one.
- Packaging: a QuillBeacon build shell (onedir spec, release script,
  portable bundle, Inno Setup installer) and, in the installer, Full /
  Compact / Custom setup types with a fixed program component and an
  optional Documentation (User Guide) component. Upgrades wipe the app's
  own internal tree before re-laying files so a renamed module can never
  leave a stale copy behind. The bundle was slimmed alongside the sibling
  apps.
- QuillBeacon has an application icon. It had none: the spec carried a
  "drop a real assets/quill-beacon.ico in once it exists" comment, and until
  then the build wore PyInstaller's generic default -- the same generic default
  as any other unbranded Python app on the machine, which in a taskbar or an
  Alt+Tab list is indistinguishable from software the listener never installed.
  QuillBeacon's icon is now a place-marker pin on a crimson tile, sharing the
  QuillVille family's rounded tile shape and amber accent. The pin is the one
  shape in the family with a point, so it cannot be confused with any sibling
  even as a blur -- fitting for an app whose whole subject is saving *places
  within things*. The installer uses it too.
- **Every release build checks its version against what is published** (2026-10-15). The shared QuillVille runtime carries every app's version number, so a build of one app could make another report a version nobody can download yet, and Check for Updates would then never offer the real one. Quill Beacon's release builds now run the same check Quill Radio, QUILL Lite, QUILL Cast and Quill Weather already did, and a build of every app at once checks them all again instead of stopping at an app it did not know.

### The first slice (2026-07-15)

First slice: Phase-1 local-first desktop MVP.

#### Engine
- SQLite + FTS5 local store with transactional migrations, WAL mode, and
  tombstoned deletes (PRD 22.1).
- Universal Location Descriptor with six locator layers and fallback
  resolution that never silently replaces an exact bookmark (PRD 10).
- Section-15 search grammar: free text, `type:`, `tag:`, `collection:`,
  `domain:`, `health:`, `has:note`, `not:archived`, phrases, and sort modes.
- Duplicate detection across canonical URLs with tracking params stripped
  (PRD 17.5).
- Capture from URL, clipboard, file, folder, podcast, and radio inputs with
  URL canonicalization (PRD 14).
- Podcast chapter normalization from Podcasting 2.0 JSON and ID3 CHAP/CTOC,
  with publisher-wins merge and personal chapters preserved (PRD 11.2).
- Import: HTML bookmarks, OPML, M3U/PLS, CSV, JSON, plain text (PRD 25).
- Export: JSON archive, HTML, Markdown, CSV, OPML, M3U, plain text (PRD 26).

#### UI
- Three-pane accessible shell: sidebar destinations/collections, virtual
  results list, details pane (PRD 13.3).
- Quick capture form and Build Search dialog (PRD 14.3, 15.4).
- Command palette (PRD 18.3, Appendix B).
- Status-bar announcements with configurable verbosity and Where Am I
  (PRD 17.6, 18.4).
- Keyboard model: no drag-and-drop required; F1 Where Am I, F6 next pane,
  F2 rename, Delete trash, Enter open (PRD 18.3). (Where Am I has since
  moved to Ctrl+F1; F1 now explains the window and the focused control.)

#### Documentation
- PRD and codebase renamed to QuillBeacon / QuillVille / QuillSync throughout.
- Section 44: grounded implementation plan mapped to the QUILL stack.
- Section 45: QuillSync server implementation plan aligned with QUILL Sync
  (git-like, E2E encrypted, BYO remote), including magic-link auth via
  Postmark (45.9).

#### Tests
- 40 engine/IO unit tests (stdlib unittest, no pytest dependency).