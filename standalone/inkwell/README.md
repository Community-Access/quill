# Quill Inkwell

Abbreviation expansion in every Windows application, built screen-reader-first,
and free.

Type `addr` and a space in a browser, a mail client, a spreadsheet, or a form,
and the address you saved appears. Type `sig.` and your signature appears with
the full stop still in place. The same abbreviations work inside QUILL's editor,
because they are the same abbreviations: Inkwell and QUILL read and write one
shared library, so anything you add in either is usable in both immediately --
no import, no export, no synchronising.

Inkwell lives in the system tray. Expansion is a background service; the window
is only where you manage the list.

## What it does

- **Expands abbreviations anywhere.** A short word plus a space or punctuation
  becomes whatever you saved: a phrase, an address, a paragraph, a template.
- **One library with QUILL.** Add an abbreviation in either app; it works in
  both. There is exactly one `abbreviations.json`.
- **Per-abbreviation settings.** Each entry decides for itself whether it is
  case sensitive, what expands it (a space, punctuation, both, or nothing at
  all), whether it adds a trailing space, what your screen reader says when it
  fires, and whether it plays a sound.
- **Categories and Quick Insert.** Group entries however you like, and press
  Ctrl+K to find one by name and insert it without remembering its trigger.
- **Variables.** `${date}`, `${time}`, `${datetime}`, `${day}`, `${month}`,
  `${year}`, `${username}`, `${clipboard}`, and `${cursor}` to place the caret.
- **Case follows your typing.** `btw` expands as written, `Btw` capitalises, and
  `BTW` shouts.
- **It refuses to type in the wrong places.** Password managers, Windows
  sign-in prompts, and the UAC dialog are excluded permanently, and you can add
  applications of your own.

## What it deliberately does not do

Inkwell keeps no clipboard history. It reads the clipboard only at the moment an
expansion containing `${clipboard}` fires, and never stores what it finds. The
clipboard belongs to you and to whichever clipboard manager you have chosen.

## Install

Quill Inkwell ships as a Windows installer and as a portable zip. Both are
self-contained: nothing is downloaded on first run.

- Installed, it shares `%APPDATA%\Quill` with QUILL and the sibling apps, which
  is what makes the shared abbreviation library work.
- Portable, it carries its own `data` folder, so the library travels with the
  stick.

## Keyboard

| Action | Keys |
| --- | --- |
| Show or hide Inkwell | Ctrl+Alt+Shift+I |
| Quick Insert (from anywhere) | Ctrl+Alt+Shift+K |
| Manage abbreviations | Ctrl+M |
| Quick Insert (in the window) | Ctrl+K |
| New abbreviation from the clipboard | Ctrl+Shift+N |
| Turn expansion on or off | Ctrl+Shift+E |
| Minimize to the tray | Ctrl+W |

## Privacy

Inkwell watches typing so that it can recognise an abbreviation. What that means
exactly, and what it refuses to do, is written out in full in
[docs/userguide.md](docs/userguide.md#privacy) and enforced in code:

- At most 64 characters are held, in memory only.
- Nothing is written to disk, logged, or sent anywhere. There is no network code
  in the expansion path at all.
- The buffer is cleared on every expansion, on Escape, on any navigation or
  editing key, whenever focus moves to another window, and whenever expansion is
  paused.
- Nothing is ever decided from the *content* of what you typed. The check that
  suppresses expansion looks only at which window has focus.
- `QUILL_SAFE_MODE=1` disables the keyboard hook entirely.

## Documentation

- [User guide](docs/userguide.md)
- [Product requirements](docs/prd.md)
- [Changelog](docs/CHANGELOG.md)

## Building

From the QUILL checkout root, with its virtual environment active:

```
pwsh standalone/inkwell/scripts/build_release.ps1
```

Artifacts land in `standalone/inkwell/dist/`: the app folder, the portable zip,
and the setup installer.

## Licence

MIT. Free, for everyone, permanently.
