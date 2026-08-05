# Quill Media Player (standalone)

The accessible QUILL media player as its own tray-resident app — audiobooks and
audio with chapter navigation, resume, bookmarks, and a precise **Go to Position
(H:M:S)** command. Keyboard- and screen-reader-first.

This folder is only the **product wrapper**. The application itself lives in the
`quill` package (`quill.apps.player`) and runs the *same* code QUILL hosts, so it
shares your library, bookmarks, resume positions, and settings — a book you start
in QUILL continues here, and vice versa (see `docs/prd.md` Section 9.11).

## Run from source

```powershell
pip install -e ".[ui]"          # from the repo root
python -m quill.apps.player     # or: python -m quill_media_player (from this folder)
```

## Build

A PyInstaller onedir build like the sibling apps (Radio / Cast / Converter),
with **libmpv bundled** so the rich DSP path works out of the box. See the
sibling apps' `.spec` files for the packaging pattern.

## Status

Core player domain (`quill/core/media`) is complete and unit-tested. The window,
menu bar, and tray are built on the shared `AppShellFrame` + the reused
`PlayerPanel`; they still need an on-device screen-reader verification pass
(NVDA / JAWS / Narrator) per the accessibility checklist before release.
