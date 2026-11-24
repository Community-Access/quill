# FUX-06 adoption: lists that stay still, across the family

**Date:** 2026-11-23
**Item:** M2 on Jeff's list. FUX-06 from the family UX plan (`git show b7c6a1a04^:complete2.md`, section FUX-06); the decisions are in `docs/design/2026-11-19-family-ux-pilots.md`.
**Pilots already done:** Quill Cast (#1958) and QUILL Lite (#1969). This audit carries the same contract to every other app's live lists.

## The contract, and the one mechanism

FUX-06 asks six things of a list that changes while somebody reads it:

1. A refresh does not move focus, restart the details or repeat unchanged data.
2. The person decides when arrivals join the list they are reading.
3. A real change to an item stays inspectable, with when it happened.
4. A filter or sort keeps the selection where it is still valid, and says when it is not.
5. Something that expired or was deleted stays recognisable; when the selected item goes, say so and land on a predictable neighbour.
6. Slow answers arriving out of order, reconnects, paging and several windows are all tested.

There is one mechanism, used everywhere, so the apps cannot drift apart:

- **`quill/core/list_follow.py`** (new, pure). `land()` picks the row: the reader's own item by identity, otherwise the row that moved into its place (the rule in `quill.core.activity.restore_index`, which the Cast pilot uses). `change_rows()` turns the rows on screen into the new rows by deleting only what left and inserting only what arrived, so the reader's row stays the *same native item* and the screen reader has nothing to re-read. `gone_sentence()` and `hidden_sentence()` are the two sentences, said once.
- **`quill/ui/list_stay_still.py`** (the Cast pilot's module, extended). `capture_report`/`restore_report` keep the selection, the focused item and the line on screen without `SetFocus`; `restore_report` now keeps the rest of a multiple selection too (`also=`). `follow_report` and `refill_listbox` (new) put both halves together for a report list and a list box.
- **`quill/ui/media/list_columns_view.set_row`** now writes only the cells whose text changed, so a two-second update no longer rewrites an unchanged row.

**What "the person decides when arrivals join" means here.** For a *feed* (Social timelines, Beacon captures) new items are held behind a count until the person shows them. For a *management list* (recordings, downloads, a queue, a playlist) an arrival is the thing the person just asked for, so it appears at once; what FUX-06 guarantees there is that the reader's own row does not move, by identity and on the same line.

## Radio, Media Player (PR: feat/m2-radio)

| List | File | How it refilled | Already met FUX-06 | Gap | Fix |
| --- | --- | --- | --- | --- | --- |
| Recordings | `quill/ui/radio/recordings_manager_dialog.py` `_refresh` | 2-second timer; rows rewritten in place by position; old row reselected by id | No-op update when nothing changed; no SetFocus | When a recording started above the reader, the old row stayed selected *and* the reader's moved row was selected, so Remove, Play and Open acted on the wrong recording. Every cell rewritten every two seconds while recording. A row removed elsewhere left a stale selection, unexplained | `follow_report` keeps exactly one row; `set_row` writes changed cells only; a fired schedule follows to its Recording row; a recording gone from disk is said once on the timer ("X is no longer in the list.") and the next row chosen |
| Find Stations results | `quill/ui/radio/results_view.py`, `station_browser_dialog.py`, `library_search.py`, `search_paging.py` | Clear and refill, row 0 selected; libraries and More Stations reselected by index on top of row 0 | No SetFocus on dropdown searches | Two rows selected after a library answered or More Stations (Enter played row 0). Late answers from an older search, an older category or an older library replaced newer results or dragged the reader back from Favorites. The Source filter dropped the reader's station silently | Row-by-row `change_rows` keeps the reader's row as the same item; one selection; request numbers drop out-of-date searches, browses, library answers and pages; library rows never switch the category; the Source filter keeps the station or says "X is not shown with this filter." More Stations lands on the first new station by identity (it was one row off when other sources were blended in) |
| Download queue | `quill/ui/radio/download_queue_dialog.py` `refresh` | `Set()` all rows, reselect by id, else the top | By identity | Every refresh redrew the list and reselected; a removed or cleared row sent the reader to the top | `refill_listbox`: rows change one by one, the selection is written only when it differs, a removed row lands on its neighbour |
| Local Media items | `quill/ui/radio/local_media_window.py` `reload` | In-place diff, reselect by id, Focus and EnsureVisible every time | In-place cells, by identity | The line on screen jumped on every scan or tag read; a file removed by a scan left nothing selected | `restore_report` keeps the line and the whole multiple selection; a file gone from the library lands on its neighbour and says so once (background changes only, never after the reader's own Remove) |
| Favorites tree (main window) | `quill/apps/radio_favorites_tree.py` `_reload_favorites_tree` | DeleteAllItems, ExpandAll, reselect a station by key else the first row | Stations by identity | A selected folder went to the first row; a removed station went to the first row; closed folders reopened | Folders and stations both by identity; a removed one lands on its neighbour; closed folders stay closed |
| Browse Stations, Favorites branch | `quill/ui/radio/browse_tree_dialog.py`, new `browse_favorites_refresh.py` | DeleteChildren and refill; "N items." said | Not refreshed until opened | The reader's row was destroyed (left on the folder), and "N items." talked over "Added X to Favorites." | The refresh is quiet and puts the reader back on their station or its neighbour |
| Media Player bookmarks | `quill/apps/player_bookmarks.py` `_refresh_bookmarks` | Clear and append, nothing reselected | — | Every Add, Edit and Remove lost the selection | `refill_listbox`: an edited bookmark stays selected, Remove lands on the next one |
| Media Player chapters | `quill/apps/player.py` `_refresh_chapters` | Rebuilt when a file opens | Not live: the whole content changes | None | None |
| YouTube live chat | `quill/ui/radio/youtube_live_chat_window.py` | Append only; Pause holds "N waiting"; Follow is opt-in | Already the FUX-06 shape | None for FUX-06 (rows are never trimmed; noted) | None |
| YouTube comments | `quill/ui/radio/youtube_comments_window.py` | Generation-guarded pages, by identity | Yes | None | None |
| Find Streams | `quill/ui/radio/find_streams_list.py` (#2007) | Frozen refill by address | Yes (the reference) | None | None |

**What the accessibility review changed (2026-11-23).** The Desktop Accessibility Specialist reviewed the Radio change before it went up. Applied: Recordings and Local Media change rows by identity (`change_rows`), not by position, so a row inserted above the reader no longer rewrites the reader's own row with its neighbour's text; `change_rows` takes the reader's key as a *pin*, so even a re-sorted list keeps their row as the same native item; the reader's row is the focused item when it is selected, and the rest of a multiple selection survives (`also=`); the "no longer in the list" sentence waits 400 ms for the screen reader to read the new row, and is said only by the window in front (`say_when_settled`), so a second Local Media window or a Recordings window behind another app keeps quiet; Find Stations checks a browse answer when it lands, not when it arrives, and ignores a stale error; More Stations finds the first new station by key; `refill_listbox` leaves a list with no selection without one; bookmark keys carry the book; the Favorites tree is not redrawn at all when nothing in it changed (Quill Radio reloads it twice after some saves); the Local Media Playlists list is refilled row by row too; Recordings' Delete no longer selects the neighbour a second time.

Accepted as they are: `wx.ListBox.SetString` on Windows deletes and re-inserts the row, so a Downloads row the reader is on is read again when its state changes (once per state, and the change is news); the Browse Stations Favorites branch still deletes its rows when a favorite is added or removed, so when the reader is standing inside that branch the screen reader reads the row they land on, once, after the "Removed" sentence. Diffing tree children in place is the next step for both trees.

**Left in Radio, with the reason.** These are refilled only by the person's own command and say what they did, so they are lower value than the above and each needs its own tree work: Browse Stations' Refresh on a station row (`browse_refresh.refresh_selected` lands on the folder), Search All Sources and Find in this Folder (no query number; a second search usually waits for the first), the ACB Media schedule Refresh (resets its filters), the TuneIn tree. Next M2 pass.

## Social, Beacon (PR: feat/m2-social-beacon)

| List | File | How it refills | Already met FUX-06 | Gap | Fix |
| --- | --- | --- | --- | --- | --- |
| Social timeline | `standalone/social/quill_social/ui/app.py` `_load_scope` / `_render_list` | Every refresh is a full scope load: clear, refill, restore the saved reading position | No SetFocus; reading position by item id | Each scheduler run and refresh says the scope and count again; the restored row is marked read again by the selection event; a vanished post sends the reader to the first unread, not a neighbour; new posts jump in at the top | See the Social PR |
| Beacon results | `quill/apps/beacon/app.py` `_refresh_results` | Virtual list; new item count; details for row 0 | — | Selection is left at the old index, so after a capture or sync it points at another beacon; details show row 0; the count is said on every automatic sync | See the Beacon PR |

## Studio, Transcribe, Weather (PR: feat/m2-studio-transcribe-weather)

| List | File | How it refills | Already met FUX-06 | Gap | Fix |
| --- | --- | --- | --- | --- | --- |
| Weather Center lists | `quill/ui/weather/weather_center_dialog.py` `_render_report` | `Set()` on four list boxes, no reselect; details forced to row 0 | No SetFocus | Selection lost on every refresh; the summary said again for unchanged data; a slow answer for an earlier location replaces the current one; an expired alert vanishes unexplained | See the Weather PR |
| Studio library tree | `quill/apps/studio.py` `_reload_library_tree`, `quill/ui/audio_studio/library_tree.py` | DeleteAllItems and rebuild after background jobs | Book by key | A book shown twice (in a pinned view and its folder) lands on the wrong copy; a removed book goes to the first header | See the Studio PR |
| Transcribe queue | `quill/ui/windows_dictation_transcribe.py` | No list: status bar, queue sentence, Activity, Notifications | Progress said in quarters | None for FUX-06 (no list moves) | None |
| Model Library | `quill/ui/dictation_models_dialog.py` | Rows rewritten in place with `SetString` | Yes | None | None |

## GitHub and WordPress Workbench (PR: feat/m2-workbench, after GH-R-150/151)

| List | File | How it refills | Already met FUX-06 | Gap | Fix |
| --- | --- | --- | --- | --- | --- |
| Every Workbench list | `quill/ui/workbench_frame.py` `_fill_list`, `workbench_frame_groups.py`, `quill/core/workbench/list_place.py` | DeleteAllItems and refill when any cell changed; land by `row_identity` | By identity; generation guard; no SetFocus; unchanged rows skipped | No line kept on screen; multiple selection dropped; nothing said when the row went or a filter hid it; the Watches poll rewrites its labels every minute and so re-reads the row | See the Workbench PR |

## Tests

Each fix has a test that fails without it: `tests/unit/core/test_list_follow.py` (the choice of row, `change_rows` against random orders, the sentences), `tests/unit/ui/test_fux06_radio_lists.py` (recordings, Find Stations out-of-order and paging, the download queue, the Favorites tree, Media Player bookmarks), and additions to the Local Media and Browse Stations tests. `tests/unit/ui/report_list_fake.py` is a headless report list that keeps each row's selected and focused state and its native identity, so a test can tell "the same row stayed" from "a look-alike was selected".
