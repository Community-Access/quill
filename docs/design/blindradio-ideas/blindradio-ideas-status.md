# BlindRadio ideas for Quill Radio: status and remaining tasks

Started 2026-11-07. This is the running record for the program: what shipped, what is
left, and what only Jeff can do. Remove an item when it is done; when everything is
done, fold the useful parts into the Radio PRD and user guide and retire this folder.

BlindRadio is by serrebidev, MIT licensed: https://github.com/serrebidev/blindradio.
The review that chose these ideas is `docs/design/blindradio-review-2026-11-07.md`.
Every module built from a BlindRadio idea credits it in its docstring.

## Files in this folder

- `networks-and-directories.md`: curated networks, IPRD, TuneIn, and the directories refused on their terms.
- `song-history-sources.md`: What the Station Played.
- `scrobbling-and-recognition.md`: scrobbling and AudD.
- `time-shift.md`: song marks, adaptive cushion, per-station buffer length.
- `dial-tuning.md`: the agreed design for dial tuning.
- `dial-tuning-built.md`: dial tuning as built, with its open items.
- `tutorials.md`: the six guided lessons for these features.

Each notes file holds the exact user-guide, PRD and CHANGELOG text, the keys, settings
and egress rows added, and what was not verified.

## Progress log

- 2026-11-07: review written; four branches built in parallel worktrees.
- 2026-11-07: merged into `feat/radio-blindradio-ideas`:
  - curated networks (20 networks, 516 channels, every address probed, 68 moved to HTTPS) and the hand-run probe `scripts/refresh_radio_networks.py`;
  - IPRD directory (By Country, By Genre, in search);
  - TuneIn lists a station once when it is both local and in a category;
  - What the Station Played (Alt+Shift+H) from seven published-playlist sources;
  - scrobbling to ListenBrainz, last.fm and Libre.fm (off by default) and AudD as a second Identify This Song service.
- 2026-11-07: refused after reading their terms: Internet-Radio.com, radio.net tag browse, Online Radio Box, Airable, vTuner.
- 2026-11-07: dial tuning design agreed with Jeff: ships off, every part a setting.
- 2026-11-07: time-shift branch merged: song marks with Save Songs from the Buffer, adaptive cushion, per-station length.
- 2026-11-07: docs folded in: Radio user guide (chapters 3, 4, 5, 6, privacy, keys, licences), Radio PRD section 31, Radio and QUILL CHANGELOGs (Help > What's New reads the Radio one), the BlindRadio MIT notice in every product's third-party notices, site pages synced.
- 2026-11-07: stale GitHub OAuth lines in `docs/design/codex.md` corrected.
- 2026-11-08: six guided lessons added (50 lessons, 330 steps); release notes 3.2, README and the site's docs page updated.
- 2026-11-08: dial tuning built and merged: off by default, seven settings, Alt+Shift+U, Go to Playing Station (Alt+Shift+P), a generated hiss, up to two warm neighbours; docs folded in.
- 2026-11-08: PR 1792 opened; CI fixes for the accessible-name inventory, announcement punctuation, persistence audit and CodeQL.

## Remaining tasks

1. Run the gates and radio tests on the final branch; PR 1792 out of draft; merge on green CI.
2. Pull `S:\QUILL`, delete its two strays (`docs/design/blindradio-review-2026-11-07.md`, an empty `quill/core/radio/radio_credentials.py`), remove `S:\QUILL-wt-br` and `S:\QUILL-wt-br-dial`.
3. Review the module budget rebaselines: `app_keymaps.py` (604), `radio.py` (1267), `browse_tree_dialog.py` (947).

## Small follow-ups found along the way

- What the Station Played has no row on QUILL's embedded radio menu (the command palette reaches it); its window is modal; it has no Refresh.
- Scrobbling has no Preferences rows in the radio inside QUILL itself; retries run only while a station plays.
- Song marks: songs ahead of the playhead are known only from the 30-second title poll, so may be marked late until reached; saved songs keep the station's format rather than the recorder's chosen one; QUILL's embedded radio menu lacks the song commands; per-station length is not on the favorites context menu.
- AudD clip not tried on an HLS station; AudD's error replies written from its docs.
- Re-read 1.FM's terms before switching its network to `api.1cloud.fm`.
- Dial tuning: the hiss plays on the default device, not the radio's chosen one; Recently Played is a menu so it does not tune; a station rested on without Enter is never counted; Go to Playing Station looks only in Browse (when main view) or Favorites.
- Global, ARN and NZME run their own apps; if one withdraws from third-party players, delete its network entry.

## Needs Jeff

- JAWS and NVDA hand checks: the new Browse branches, What the Station Played, the Preferences rows for scrobbling and recognition, and (when built) dial tuning.
- A real scrobble: sign in to ListenBrainz and last.fm, listen for a minute, confirm it arrives.
- Register Quill Radio with last.fm (last.fm/api/account/create) and put the key and secret in the build environment for `tools/generate_lastfm_api_key.py`. Until then listeners paste their own pair.
- One AudD request with a bad token, to confirm the error wording.
- Dismiss CodeQL alert 84 (last.fm's required MD5) as won't fix: https://github.com/Community-Access/quill/security/code-scanning/84
- Dial tuning by ear: the hiss level against speech, the loop seam, a neighbour promoted with no gap, and how JAWS and NVDA read the Preferences box.
