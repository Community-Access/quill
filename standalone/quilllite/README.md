# QuillLite

**QUILL with everything removed except the editor.** Numbered documents in one
window, plain text or rich text, and nothing else.

QuillLite is for the person who wants Notepad or WordPad with QUILL's
accessibility and finds the full writing environment more than they need. It is
a companion to [QUILL for All](https://github.com/Community-Access/quill), not a
replacement: they install side by side and neither touches the other's settings.

Windows · MIT · part of the QuillVille family

---

## What it is

- **Notepad's and WordPad's keys**, unchanged, so there is nothing to learn.
- **A status bar you can read** — ten focusable cells, F6 to get in, including
  the encoding and the line endings no other editor shows you.
- **Files come back unchanged.** Encoding, byte order mark, line endings and the
  final newline all survive a round trip.
- **Bookmarks, structural selection, a copy tray, a clip library, abbreviations,
  and the tools** you actually need to do things to text.
- **Every window answers F1** with what it is for and what you are on.
- **Speech to NVDA and JAWS only**, saying only what your screen reader will
  not.
- **Spelling that tells you what is wrong**, not just that something is: land on
  a misspelling and it spells the word out, in letters or the phonetic alphabet,
  after a pause you can outrun. The Applications key opens with the corrections.
- **Earcons for the moments speech cannot cover** — cut, copy, paste, delete,
  undo, save, close — every one of them replaceable with a sound of your own,
  and **Alt+Shift+M** silences the lot.
- **Switchable.** Turn rich text off and it is Notepad; turn everything on and it
  is WordPad with tools. Four one-word profiles set every switch at once.

New here? Start with [the announcement](docs/announcement.md) — it is the
one-page version, written for somebody who has never opened it.

Full detail is in [the user guide](docs/userguide.md); the reasoning is in
[the product requirements](docs/prd.md); what changed and why is in
[the changelog](docs/CHANGELOG.md) and
[the release notes](docs/release-notes-1.0.md).

---

## Install

Four downloads. You want one of them.

| Download | Take this one if |
|---|---|
| `QuillLite-Setup-Shared-<version>.exe` | You want the normal installer. Everything is in it. |
| `QuillLite-Lite-Setup-<version>.exe` | You already have another QuillVille app, or you would rather the shared runtime downloaded on first launch. |
| `QuillLite-Portable-<version>.zip` | You want it on a USB stick, settings and recovered work included. |
| `QuillLite-Companion-<version>.zip` | You already have the QuillVille runtime and want only the launcher. |

The full installer offers *Open .txt and .rtf files with QuillLite* as an
**optional** component. It adds QuillLite to the Open With list and never
becomes the default handler — Notepad, WordPad and QUILL stay where they were.

**SmartScreen.** Until code signing is in place, Windows may warn about the
installer. Choose **More info**, then **Run anyway**.

---

## Run from source

QuillLite lives in the `quill` package (`quill.apps.lite`); this folder is the
product wrapper — entry point, icon, installers, docs.

```powershell
# from the QUILL checkout root
pip install -e ".[ui,dev]"
python -m quill.apps.lite
```

Or use the dev launcher, which finds a venv for you:

```powershell
.\run-quill-lite.bat
```

Useful switches:

```
python -m quill.apps.lite [--rich | --plain] [--new-instance] [--check] [file ...]
```

`--check` writes a diagnostic to the data folder and exits without opening a
window: whether the native Rich Edit surface came up, which text mode it is in,
whether a screen reader is reachable, and where the data lives. It is the first
thing worth asking for in a support conversation, and the only way to smoke-test
a frozen build without disturbing a running copy.

---

## Build a release

```powershell
.\scripts\build_release.ps1              # all four artifacts
.\scripts\build_release.ps1 -Sign        # …signed (see docs/code-signing.md)
.\scripts\build_release.ps1 -SkipSharedRuntime   # reuse a runtime another app built
```

Docs are rendered to HTML and EPUB from the Markdown by
`scripts/render_docs.ps1`, which `build_release.ps1` runs first.

---

## Where your data lives

```
%LOCALAPPDATA%\QuillLite
```

Settings, recent files, the copy tray, and any recovered work. Deliberately
**not** `%APPDATA%\Quill`: QuillLite is offered as an alternative to QUILL, and
a machine that has never had QUILL installed should not grow a Quill folder
because somebody opened a text file. Uninstalling does not remove this folder —
recovered work is the one thing you might not have finished with.

A portable build keeps the same folder on the stick instead.

---

## Provenance

QuillLite began as [PR
#1490](https://github.com/Community-Access/quill/pull/1490) by Steven Scott
(`doubletaponair`), offered under this repository's MIT licence — together with
a standalone reproduction of a real bug in QUILL's Rich Edit surface, which
ships here as `tests/repro_tom_true.py` and imports neither QUILL nor QuillLite
so it can be run against a clean checkout. Both that fix and a second one are in
this release, and both reach every QUILL user rather than only QuillLite's.
