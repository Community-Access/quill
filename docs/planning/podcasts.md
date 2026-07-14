# Podcasts in QUILL — Remaining Work

## Still to build

**Transcripts & export.** If a feed carries a `<podcast:transcript>` link:
Save Transcript As... and Open Transcript in Editor (as a new QUILL document,
never overwriting the source). If absent: Transcribe Episode... routes the
downloaded audio through QUILL's existing transcription engines
(`core/ai/transcription.py`, the same path the Listening Companion uses),
offering to download first if needed. Either way, the transcript should
chain into Transcript Actions (Executive Summary, Show Notes, Key Quotes).
Export... copies downloaded audio file(s) to a chosen folder, named from the
real show/episode title, offering to download first if needed.

**The Inbox.** A second, independent nested folder tree (`InboxFolder`,
separate from the library folder tree) that organizes *episodes* rather than
shows, cutting across library placement entirely. A show marked
`route_to_inbox` (the field already exists on `PodcastShow`, unsurfaced) has
its new episodes appear in the Inbox regardless of library folder; episodes
can be manually filed into Inbox-only folders. The first manual placement of
an episode from a given show should be remembered
(`inbox_default_folder_id`, also already on the model) and auto-file future
episodes from that show there, with a Forget Remembered Folder action to
revert to manual filing. Excluded from OPML both directions (no OPML
equivalent for a local curation layer).

**Virtual views.** Three pinned nodes at the top of the library folder tree:
**Favorites** (every show with `is_favorite` — the field exists, unsurfaced),
**New Episodes** (every unplayed episode across all subscriptions, newest
first; wire through `core/notifications.py`, off by default and opt-in per
show, exactly one notification per new episode, never a digest/reminder),
and **Continue Listening** (in-progress episodes by `position_ms`,
most-recently-listened first — no new state needed, resume position already
persists).

**Play Queue.** Cross-show, ordered list (`PlayQueue`) with Play Next / Add
to Queue on any episode. Reordering: Move Up/Down for single-slot nudges,
plus Mark for Move + Move Marked Item Above/Below for long-distance moves —
matches QUILL's existing accessible-reordering pattern (e.g. Interactive
Rebase's commit list). Remove from Queue / Clear Queue.

**Local (imported) podcasts.** Add Local Podcast... — pick audio file(s) or
a folder; QUILL copies them into the podcast storage location as a new
`is_local: true` show, one episode per file, title guessed from the
filename (`core/speech/audiobook.py::title_from_filename`). A file's own
chapters (m4b, or ID3) populate its chapter list through the existing
chapters machinery — no new chapter code needed. Not exported to OPML.
**Not synced**: since QUILL Sync works by pointing the whole configured data
directory at a synced folder, local-podcast records need to live outside
that directory by construction, not by a "please don't sync this" promise —
exact path TBD at implementation time. **Watched folder** (optional,
Downcast-inspired): point a local podcast at a watched folder (reusing
`core/watch_audiobook.py`'s pattern) so a dropped audio file becomes a new
episode automatically.

**Episode notes/annotations.** A timestamped note on a moment in an episode,
reusing QUILL's existing Sticky Notes / Inline Notes system rather than a
parallel one. A "My Notes in this Episode" list jumps to any note's
timestamp.

**Rich filtering.** A View/Sort toolbar already ships sorting; still needed:
episode filters (All / Unplayed / Played / Downloaded / Not Downloaded),
show filters (All / Favorites Only / Has Unplayed Episodes), and an
always-visible **Search Everywhere** action that broadens local search to
every subscription/episode/transcript/note at once, grouped by type
(distinct from the existing context-aware scoped search and from the
separate iTunes discovery search).

**Auto-trim silence / loudness normalization / volume boost.** Auto-trim and
loudness-normalize (optional, per show) reuse the exact functions the
audiobook builder already uses (`core/speech/audio_edit.py`,
ACX-normalization ffmpeg pass) — download-time processing, not live. Volume
boost is a separate live-playback gain control for pushing quiet audio
louder on the fly without reprocessing the file.

**Always Sync.** `always_sync_full_catalog` (per show): beyond the routine
"newer than what I have" refresh every show gets, backfills every older
episode the live feed still exposes into the local catalog (and downloads
it too, if that show is in download mode). Implementation note: this is in
tension with `keep_last_n` retention (backfilling the whole catalog while
immediately pruning to N fights itself) — nudge toward `keep_all` in the
settings UI when Always Sync is on.

## Not-yet-built modules

From the original architecture sketch, still to add:

```
quill/core/podcasts/
  local_store.py   # atomic-JSON store for is_local shows -- deliberately
                    # outside the syncable data directory
  inbox.py          # InboxFolder tree + routing/remembered-folder logic
  queue.py           # PlayQueue

quill/ui/podcasts/
  episode_notes_panel.py
```
