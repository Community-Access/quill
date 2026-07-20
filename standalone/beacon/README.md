# QuillBeacon

*Find your way back to anything.*

QuillBeacon is an accessible, local-first bookmark and location manager in
the QUILL family. It saves not just *things* but exact *places within
things* -- a web heading, a document passage, a podcast chapter, a radio
moment, a file, a folder -- and gets you back to them in seconds, privately,
with the original context preserved.

This repo is the standalone companion app, following the pattern set by
[Quill Cast](https://github.com/Community-Access/quill-cast) and
[Quill Radio](https://github.com/Community-Access/quill-radio). The full
product requirements and implementation plan live in
[Docs/PRD.md](Docs/PRD.md) (see section 44 for the grounded implementation
plan and section 45 for the QuillSync server plan).

## Status

First slice: Phase-1 local-first desktop MVP (PRD 44.2).

- Engine: SQLite + FTS5 store, the Universal Location Descriptor (ULD) with
  multi-layer fallback resolution, the section-15 search grammar, capture,
  podcast/radio chapter normalization, and import/export across open formats.
- UI: three-pane accessible wx shell (sidebar / results / details), quick
  capture form, Build Search dialog, command palette, status-bar
  announcements, and a keyboard model with no drag-and-drop required.
- Out of scope for this slice: QuillSync encrypted sync, the built-in media
  player, iOS, and intelligent assistance (PRD phases 2-5).

## Run from source

Requires Python 3.12+ and wxPython.

```
pip install wxPython
run-quill-beacon.bat        # Windows
python launcher.py         # any platform
```

The local store lives under the platform app-data directory
(`%APPDATA%\QuillBeacon` on Windows), or next to the exe in portable mode.

## Tests

Pure-logic engine tests run without a display:

```
python -m unittest discover tests
```

## Architecture

```
quill_beacon/
  model.py      dataclasses: Resource, Beacon, Location, Collection, Tag, Trail
  db.py         SQLite + FTS5 persistence, migrations, tombstones
  uld.py        Universal Location Descriptor + fallback resolution
  search.py     query grammar, FTS5 + structured filters, sort, duplicates
  capture.py    canonicalization + capture from URL/clipboard/file/folder
  media.py      podcast chapter normalization (Podcasting 2.0, ID3), radio
  importers.py  HTML, OPML, M3U/PLS, CSV, JSON, plain text
  exporters.py  JSON, HTML, Markdown, CSV, OPML, M3U, plain text
  announce.py   accessible status-bar announcements + Where Am I
  dialogs.py    quick capture form, Build Search dialog
  commands.py   command palette
  app.py        three-pane wx shell, menus, actions
tests/
  test_engine.py   db, model, ULD, search
  test_io.py        capture, importers, exporters, media
```

The production target moves the engine into `quill/apps/beacon.py` on
`quill.ui.app_shell.AppShellFrame`, with this repo becoming a thin wrapper
that depends on `quill[ui]` -- exactly how Quill Cast and Quill Radio are
structured.

## License

MIT.