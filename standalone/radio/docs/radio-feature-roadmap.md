# Quill Radio — station-browsing roadmap

Target capabilities to make station discovery in Quill Radio comprehensive and
fully keyboard/screen-reader native. This is our own roadmap; it names no other
product.

## Already shipped

- **Search across every directory at once** (RadioBrowser, SomaFM, iHeart,
  TuneIn), with Tag and Country dropdowns, plus NOAA Weather Radio and Radio
  Reading Services by name / SAME code / call sign.
- **Browse tree** with Radio Browser (by genre), TuneIn's real folder tree
  (**location drill-down to city**), iHeart (genre → A–Z), SomaFM, Weather/NOAA
  (1,035 transmitters, offline), ACB Media, NFB Radio, Radio Reading Services,
  and the Community M3U / Xiph catalogs.
- **Add custom station** by URL, with YouTube / Live365 / SecureNet / Triton
  resolution and a self-healing stream-repair ladder.
- Recording (now + scheduled), sleep/wake timers, DVR (pause/rewind live),
  favorites with folders, global hotkeys, tray with favorites, sound-card
  routing with fallback, backup/restore, braille output.

## Planned additions

1. **Networks section** — well-known broadcasters as one-click browse nodes
   (public broadcasters worldwide, US news/talk, US public radio, sports, music,
   plus honest affiliate-search nodes for syndication services). All resolved
   through the already-integrated Radio Browser directory, so no new
   network-egress site, no API keys, and no third party's curated list is
   copied. See `networks-catalog.md`. *(Core module landed; browse-tree wiring
   next.)*
2. **Three-band equalizer** — Bass / Mid / Treble (−12…+12 dB) with presets
   (Flat, Bass Boost, Treble Boost, Loudness, Voice, Warm), toggled with
   `Ctrl+E` and switchable from anywhere with `Ctrl+Alt+Shift+E`, hosted on the
   mpv audio-filter chain.
3. **Quick-play favorites** — `Alt+1`…`Alt+0` play the first ten favorites
   directly, rebindable in the Keyboard Manager.
4. **Browse position memory** — reopening Browse Stations returns to the node
   you were on, with its ancestors expanded, instead of a collapsed top level.
