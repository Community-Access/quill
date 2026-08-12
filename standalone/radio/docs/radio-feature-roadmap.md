# Quill Radio -- station-browsing roadmap

Target capabilities to make station discovery in Quill Radio comprehensive and
fully keyboard/screen-reader native. This is our own roadmap; it names no other
product.

An item leaves "Planned" only when it is actually reachable in the app -- wired
to a menu or command, not merely present as a core module.

## Already shipped

- **Search across every directory at once** (RadioBrowser, SomaFM, iHeart,
  TuneIn), with Tag and Country dropdowns, plus NOAA Weather Radio and Radio
  Reading Services by name / SAME code / call sign.
- **Browse tree** with Radio Browser (by genre), TuneIn's real folder tree
  (**location drill-down to city**), iHeart (genre to A-Z), SomaFM, Weather/NOAA
  (1,035 transmitters, offline), ACB Media, NFB Radio, Radio Reading Services,
  and the Community M3U / Xiph catalogs.
- **Add custom station** by URL, with YouTube / Live365 / SecureNet / Triton
  resolution and a self-healing stream-repair ladder.
- Recording (now + scheduled), sleep/wake timers, DVR (pause/rewind live),
  favorites with folders, global hotkeys, tray with favorites, sound-card
  routing with fallback, backup/restore, braille output.
- **Networks section** -- well-known broadcasters as one-click browse nodes
  (public broadcasters worldwide, US news/talk, US public radio, sports, music,
  plus honest affiliate-search nodes for syndication services). All resolved
  through the already-integrated Radio Browser directory, so no new
  network-egress site, no API keys, and no third party's curated list is copied.
  See `networks-catalog.md`. Core in `core/radio/networks.py`, wired into the
  browse tree.
- **Three-band equalizer** -- Bass / Mid / Treble, -12 to +12 dB each, freely
  adjustable, with a Quick preset shortcut (Flat, Bass Boost, Voice Clarity,
  Podcast, Small Speakers, Late Night) that sets all three at once. Lives in
  **Playback > Sound Enhancements...** alongside the compressor, channel mode,
  night mode, and OptiLab broadcast polish, and previews live as you move a
  slider. Every setting is remembered per station as well as shared. (Shipped
  through the Sound Enhancements dialog rather than the `Ctrl+E` /
  `Ctrl+Alt+Shift+E` chords this roadmap originally sketched.)
- **Quick-play favorites** -- ten commands play the first ten favorites
  directly. They default to `Ctrl+Alt+Shift+1`...`Ctrl+Alt+Shift+0` rather than
  the `Alt+1`...`Alt+0` sketched here, because the plain and Alt digit combos
  are already bound to window navigation, headings, and the copy tray; rebind
  them in the Keyboard Manager if you do not use those.
- **Browse position memory** -- reopening Browse Stations returns to the node
  you were on, with its ancestors expanded, instead of a collapsed top level.
- **Song history** -- a per-station log of every track change, with copy, send
  to the Clip Library, and an optional AI background note on a song (labelled as
  model-written, never available in Safe Mode). Playback > Song History.
- **One volume for every station** -- **Use One Volume for All Stations**
  (Playback menu) makes a single level answer for every station, so Volume
  Up/Down turn *everything* up or down instead of only the station you are on.
  Per-station levels are kept rather than erased, so turning it back off restores
  them; **Forget Every Station's Own Volume...** clears them deliberately, after
  confirming.

## Planned additions

Nothing outstanding on station browsing. The next radio work is tracked in
`planning.md` (the directory-expansion workstream: FMSTREAM, SHOUTcast, Icecast
and RadioDNS behind one canonical station record).
