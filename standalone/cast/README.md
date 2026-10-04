# QUILL Cast

QUILL Cast is a podcast app for Windows, made for people who use a screen
reader. Everything works from the keyboard, every list says what is in it,
and Cast tells you what it did after you press a key.

It is part of the QUILL family, from Community Access. If you also use QUILL
or Quill Radio, they share one library with Cast: follow a podcast in one and
it is there in the others.

Version 2.0.0, released 2026-10-03.

## What you can do with it

- Follow podcasts by name, by feed address, or from another app's OPML file.
  Private feeds with a username and password work too.
- Move around one window: the Inbox, New Episodes, Continue Listening,
  Favorites, Playlists, the Play Queue, Downloads and your podcasts are all
  places in a list, each one key away.
- Listen with the keys you would expect: skip, chapters, speed, a sleep
  timer, bookmarks, and a Now Playing window with the show notes and their
  links.
- Let Cast keep up for you. Each podcast can be checked on its own schedule,
  new episodes can download on their own, and notifications wait for you if
  you were busy.
- Turn off anything you do not use. Customize Features hides a whole feature,
  menu rows and all.
- Add your own recordings and audiobooks as Personal Audio.

## Install

Download `QUILL-Cast-Setup-<version>.exe` from the Releases page and run it.
If you would rather not install anything, the portable zip runs from any
folder or USB stick and keeps your library in its own `data` folder.
Everything Cast needs is in the download, including ffmpeg.

## Documentation

- [User Guide](docs/userguide.md): start here.
- [Release Notes](docs/release-notes-2.0.md): what QUILL Cast 2.0.0 can do.
- [Tutorials](docs/tutorials.md): the guided lessons that are also in Help > Tutorials.

Questions, or something not working? Write to support@community-access.org
and a person will answer.

## For developers

QUILL Cast is not a fork. The app lives in the
[quill](https://github.com/Community-Access/quill) package
(`quill.apps.podcasts`) and runs the same podcast code QUILL uses. This folder
holds the entry point, the installer and the documentation.

Run from source:

```powershell
pip install .
quill-cast
# or, with the quill package already installed:
python -m quill.apps.podcasts
```

Build every release artifact (the app folder, a portable zip and the
installer; needs Inno Setup and an ffmpeg.exe to bundle):

```powershell
.\scripts\build_release.ps1 -FfmpegDir C:\path\to\ffmpeg\bin
```

The [Changelog](docs/CHANGELOG.md) and the [Product Requirements](docs/prd.md) are
the engineering record.

## License

MIT, same as QUILL. See [LICENSE](LICENSE).
