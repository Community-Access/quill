# Changelog

## Unreleased

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