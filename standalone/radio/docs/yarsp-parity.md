# Quill Radio vs. YARSP 0.5.0 — feature parity check

Source: YARSP page (l-works.net/yarsp.php) and manual
(l-works.net/docs/yarspmanual.html), studied for **ideas only** — none of
YARSP's station data or curated lists are copied. Interop stays via open
standards and open directories (Radio Browser, SomaFM's own API, each
network's public streams).

## Verdict

Quill Radio **meets or exceeds** YARSP on almost every axis. The one clear
gap that maps to the request is a curated **Networks** section (BBC, NPR, and
friends as one-click entries). "Drill down by city" already exists via TuneIn.

## Parity table

| Capability | YARSP | Quill Radio | Status |
| --- | --- | --- | --- |
| Search all directories at once (name/genre/country/language) | yes | Search Stations across RadioBrowser + SomaFM + iHeart + TuneIn, with Tag and Country dropdowns; also NOAA/reading-services by name/SAME/call sign | Parity+ |
| Radio Browser by genre/country | yes | "Radio Browser (by Genre)" browse branch + country via search dropdown | Parity |
| TuneIn continent → **city** | yes | TuneIn's real folder tree (browse) drills to city | **Parity (city drill-down already shipped)** |
| iHeartRadio by genre | yes | iHeart → genres → A–Z stations | Parity+ |
| **Networks: BBC, NPR, CBC, ABC Australia, Radio France, Deutschlandfunk, SomaFM** | yes | **SomaFM only** (plus ACB Media, NFB Radio, Radio Reading Services) | **GAP** |
| Add custom station by URL | yes | Add Custom Station (+ YouTube, Live365, SecureNet resolution) | Parity+ |
| Browse remembers position | yes | to confirm | Verify |
| Favorites reorder (Alt+arrows), folders | yes | Favorites tree + Manage Favorites, Move/Move-to-Folder, folders | Parity+ |
| Recently played | yes | Recently Played (last 15) | Parity |
| Quick-play first 10 (Alt+1…Alt+0) | yes | Play Last Station + Recently Played, but **no Alt+1…0 direct favorite play** | Likely GAP (small) |
| 3-band equalizer + presets, hotkeys | yes | mpv "Sound Enhancements" + Volume Boost + night mode; **no labeled 3-band EQ with presets** | Likely GAP (different design) |
| Global hotkeys (rebindable, work hidden) | yes | Global Hotkeys… + Keyboard Manager | Parity |
| Track title in title bar + change announcements (toggle) | yes | Now Playing + What's Playing + announcements | Parity |
| Sound-card selection + fallback | yes | Radio output device routing + remembered/fallback | Parity |
| Brief dropout handling + retry | yes | Ride-out + self-healing stream repair ladder | Parity+ |
| Tray icon w/ controls + favorites | yes | Tray: Play/Stop, Favorites (nested), Recently Played, Record, Schedule, Browse | Parity+ |
| Hide window, keep playing | yes | Send to Tray (Ctrl+W), Alt+F4-to-tray option | Parity |

## Where Quill Radio already goes beyond YARSP

Recording (Record Now + scheduled + wake/sleep timers), the full 1,035-transmitter
NOAA Weather Radio directory (offline), Radio Reading Services + ACB Media + NFB,
braille output of announcements, YouTube/Live365/SecureNet/Triton stream
resolution, DVR (pause/rewind live), backup/restore, M3U import/export, the
Weather Center, multi-window UI, and the status bar.

## Plan to close the gaps

### 1. Networks section (the request) — recommended: curated Radio Browser queries

Add a **Networks** top-level branch to Browse Stations with child nodes for
**BBC, NPR, CBC, ABC Australia, Radio France, Deutschlandfunk** (SomaFM already
ships and can sit here too). Each node is a **curated Radio Browser query**
(by name/tag/country) rather than a new upstream:

| Network | Open source | Notes |
| --- | --- | --- |
| BBC | Radio Browser (name "BBC", country "United Kingdom") | World Service is global; some HLS is UK-geofenced |
| NPR | Radio Browser (tag "npr"/"public radio") | NPR's own API needs a key + is on-demand; RB is the clean path |
| CBC | Radio Browser (name "CBC", country "Canada") | |
| ABC Australia | Radio Browser (name "ABC", country "Australia") | ABC also has a public API |
| Radio France | Radio Browser (name "France Inter/Info/…") | Radio France has a public API too |
| Deutschlandfunk | Radio Browser (name "Deutschlandfunk") | public streams also documented |
| SomaFM | already integrated via SomaFM's own channels.json | keep native |

**Why Radio Browser queries:** it is already integrated (`radio_browser.py`),
so this adds **no new network-egress site** (keeps `network_egress_audit`
green), no API keys, no per-network maintenance of expiring stream URLs, and no
copying of anyone's curated list. "Stream Madness" is deliberately **not**
replicated — it is YARSP's own curation (competitor data).

Implementation: a small `quill/core/radio/networks.py` defining the curated
queries, surfaced as browse-tree kinds in `browse_tree_dialog.py` and as an
optional Source in `directory_search.py`; unit tests; userguide/PRD/CHANGELOG.

### 2. Quick-play Alt+1…Alt+0 for the first ten favorites (small)

Bind Alt+1…Alt+0 to play favorites 1–10 directly (rebindable via the Keyboard
Manager), matching YARSP's fast path.

### 3. Equalizer (evaluate)

Decide whether to surface a labeled 3-band EQ with presets on top of the mpv
audio filter chain (Quill Radio already has the mpv engine that can host an
`equalizer`/`superequalizer` filter), or document the existing Sound
Enhancements as the equivalent.

### 4. Browse position memory (verify)

Confirm whether Browse reopens on the last node; add if missing.
