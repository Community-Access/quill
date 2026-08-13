# Changelog

All notable changes to Quill Converter are documented here. See
`docs/release-notes-1.0.md` for the fuller narrative version.

Quill Converter is the product wrapper; the application code lives in the
`quill` package, so the entries below are drawn from the commit history of
`quill/apps/converter.py`, the shared conversion engine under
`quill/core/audio/`, the shared Convert Audio dialog, and this folder.

## Unreleased

- **The tile icon moved to the family generator.** Quill Converter's icon was
  already generated rather than hand-drawn -- it had its own
  `assets/make_quill_converter_icon.py` -- which made it the only app in the
  family whose icon could be reviewed in source. That idea was right and has
  been generalised: `scripts/build_app_icons.py` at the repository root now
  draws every app's icon from one design system, and Converter's private
  generator has been retired. The drawing is unchanged in concept (two arrows
  passing in opposite directions, on a violet tile); what changed is that no two
  apps can now drift apart, or collide, because a test asserts that no two
  render the same face.

## 1.0.0 - 2026-07-31

The first release: the Universal Audio Converter as its own tray-resident
Windows app.

### The app

- Standalone Quill Converter app: a small window whose whole job is audio
  conversion -- a queue, an output format, a preset, an output folder, and a
  Convert button. Single-instance, tray-resident, with a show/hide global
  hotkey (Ctrl+Alt+Shift+C) and the shared QuillVille menu for opening the
  sibling apps. Focus lands on the queue the moment the window opens.
  (2026-07-31)
- Windows Explorer verb: right-click an audio or video file and choose
  **Convert with Quill** to open it in Quill Converter, already queued. Off by
  default; turn it on in QUILL's settings ("Offer Convert with QUILL").
  (2026-07-31)
- Standalone build entry and tile icon, produced by the shared QuillVille
  portable builder. (2026-07-31)

### The conversion engine (shared with QUILL and Audio Studio)

- Universal audio converter core: a mixed file/folder queue, folder scanning
  with source-tree mirroring, a conflict policy that never overwrites an
  original unless asked, atomic writes, multi-worker batching, and a spoken
  end-of-run summary that names the files that failed. Output formats are
  probed against the resolved FFmpeg so the app never offers a format it
  cannot actually encode. (2026-07-30)
- One-click presets: Just convert, MP3 320 / 192 / 128, Podcast, Audiobook
  (M4B), Voice memo, Web voice (Opus), Archival (FLAC), and Hearing-aid mono.
  (2026-07-30)
- Convert Audio dialog and its Audio Studio entry: the accessible, house-
  contract dialog behind the **Advanced...** button, with a real Convert /
  Cancel pair, a Delete-to-remove queue, and named controls throughout.
  (2026-07-30)
- Advanced-mode DSP catalog, revealed by an **Advanced options** checkbox:
  bit rate, sample rate, channels, bit depth, loudness normalization
  (audiobook / podcast targets), gain, a rumble-removing high-pass, silence
  trimming, a compressor, and a volume leveler. Every control starts on a
  neutral "leave the preset alone" choice. (2026-07-30)
- Speed (tempo) and fade in / fade out added to the Advanced panel.
  (2026-07-30)
- **Convert from URL...**: paste a link, Quill Converter downloads its audio
  and drops it straight into the converter. yt-dlp is not bundled -- the first
  use asks once, shows a plain rights notice, and installs the component on
  demand. Unavailable in Safe Mode. (2026-07-30)
- Headless `quill convert` command over the same engine, with `--dry-run`,
  `--list-presets`, and the whole option set on the command line.
  (2026-07-30)

### Fixes

- Conversion progress now travels through the shared background-task callback,
  so the status bar, the tray tooltip, and the spoken milestones all update
  together and a batch stays reviewable while the window is minimized.
  (2026-07-30)
- The Convert Audio dialog is a real `wx.Dialog` subclass, so it is shown
  through the accessible modal-dialog path like every other dialog in the
  family. (2026-07-30)
