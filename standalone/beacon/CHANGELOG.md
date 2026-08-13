# Changelog

## Unreleased

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
- QuillBeacon now speaks (#1283, #1300). Every announcement went to the
  status bar (or, failing that, the window title) and nowhere else, and
  screen readers announce neither on their own -- so "QuillBeacon ready",
  result counts, filter changes and undo confirmations were silent.
  Announcements now also go through the shared announcement service, which
  speaks them through your screen reader and writes them to a connected
  braille display. The status bar still updates as the visual floor, and
  every existing announcement call site gained speech without changing.
- Destructive confirmations default to No: permanently deleting selected
  items, deleting a smart collection, and removing an attachment all open
  their Yes/No prompt with No preselected, so a stray Enter or Space
  cannot destroy anything.
- Every dialog answers Escape and Enter (WCAG 2.1.2). Twenty dialogs plus
  the command palette were built without the shared modal-id contract, so
  Escape and Enter were not mapped to their own Cancel/OK/Close buttons --
  a keyboard trap. All of them now wire the contract, using only ids that
  a real button backs.
- The built-in media player runs on the family's shared audio layer, so it
  inherits the default wx.media backend plus the opt-in libmpv backend
  (gapless playback, exact seeking, output-device routing). With no
  backend available at all it announces "media backend unavailable"
  instead of failing.
- Outbound-URL safety for anything the user (or an imported OPML file)
  supplies: feed fetches and link-health checks now refuse non-http(s)
  schemes and hosts that resolve to private, loopback, or link-local
  addresses, and cap the response body, so a pasted URL cannot be used to
  reach the local network or stream unbounded data into memory.
- Location resolution gained a final fallback layer (PRD 10.2): after the
  built-in native / structural / text-quote / fuzzy / positional locators
  all fail, an extension-contributed `beacon.resolver` may place the
  location, always at a needs-review confidence so it can never silently
  replace an exact bookmark. A sample resolver extension ships with QUILL.
  This is groundwork: QuillBeacon does not host extensions yet, so the
  layer has nothing to consult on a stock install.
- Packaging: a QuillBeacon build shell (onedir spec, release script,
  portable bundle, Inno Setup installer) and, in the installer, Full /
  Compact / Custom setup types with a fixed program component and an
  optional Documentation (User Guide) component. Upgrades wipe the app's
  own internal tree before re-laying files so a renamed module can never
  leave a stale copy behind. The bundle was slimmed alongside the sibling
  apps.
- Capture routing rules (PRD 14.5, 44.11): an ordered keyword -> folder list
  files new web bookmarks automatically. First matching rule wins; each
  keyword can be used by only one rule. Applied at every web capture surface
  (extension bridge, native messaging, quick capture, CLI, imports) unless
  the user explicitly chose a folder; routed bookmarks still land in the
  Inbox. Edited under Preferences > Routing Rules with keyboard-only
  reordering.

## 0.1.0 - 2026-07-15

First slice: Phase-1 local-first desktop MVP.

### Engine
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

### UI
- Three-pane accessible shell: sidebar destinations/collections, virtual
  results list, details pane (PRD 13.3).
- Quick capture form and Build Search dialog (PRD 14.3, 15.4).
- Command palette (PRD 18.3, Appendix B).
- Status-bar announcements with configurable verbosity and Where Am I
  (PRD 17.6, 18.4).
- Keyboard model: no drag-and-drop required; F1 Where Am I, F6 next pane,
  F2 rename, Delete trash, Enter open (PRD 18.3).

### Documentation
- PRD and codebase renamed to QuillBeacon / QuillVille / QuillSync throughout.
- Section 44: grounded implementation plan mapped to the QUILL stack.
- Section 45: QuillSync server implementation plan aligned with QUILL Sync
  (git-like, E2E encrypted, BYO remote), including magic-link auth via
  Postmark (45.9).

### Tests
- 40 engine/IO unit tests (stdlib unittest, no pytest dependency).