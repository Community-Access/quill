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
- `time-shift.md`: song marks, adaptive cushion, per-station buffer length (arrives with its branch).
- `dial-tuning.md`: the agreed design for dial tuning (not built yet).

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

## Remaining tasks

1. Merge the time-shift branch (`feat/br-shift`): song marks in the buffer, adaptive cushion, per-station buffer length.
2. Fold each notes file's text into the Radio user guide, PRD, CHANGELOG and What's New; add the BlindRadio MIT notice to the third-party notices; regenerate HTML and EPUB.
3. Run `platform_report`, regenerate snapshots, re-run the menu-accelerator gate and the radio test suite on the merged branch.
4. PR to main; merge on green CI.
5. Remove the program's worktrees once their branches are on main.
6. Build dial tuning to `dial-tuning.md` (after time-shift, since both change the mpv engine), as its own PR.
7. Correct stale GitHub OAuth lines in `docs/design/codex.md` (542, 1018, 1590): the per-app OAuth Apps were registered on 2026-11-02 and their client ids are built into `quill/core/ai/copilot_auth.py`.

## Small follow-ups found along the way

- What the Station Played has no row on QUILL's embedded radio menu (the command palette reaches it); its window is modal; it has no Refresh.
- Scrobbling has no Preferences rows in the radio inside QUILL itself; retries run only while a station plays.
- AudD clip not tried on an HLS station; AudD's error replies written from its docs.
- Re-read 1.FM's terms before switching its network to `api.1cloud.fm`.
- Global, ARN and NZME run their own apps; if one withdraws from third-party players, delete its network entry.

## Needs Jeff

- JAWS and NVDA hand checks: the new Browse branches, What the Station Played, the Preferences rows for scrobbling and recognition, and (when built) dial tuning.
- A real scrobble: sign in to ListenBrainz and last.fm, listen for a minute, confirm it arrives.
- Register Quill Radio with last.fm (last.fm/api/account/create) and put the key and secret in the build environment for `tools/generate_lastfm_api_key.py`. Until then listeners paste their own pair.
- One AudD request with a bad token, to confirm the error wording.
