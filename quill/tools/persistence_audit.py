"""GATE: every persisted store declares its release-to-release posture.

The companion to ``network_egress_audit.py``, for *persistence* instead of
network egress. It AST-scans ``quill/`` for ``write_json_atomic`` call sites --
the one primitive every JSON store goes through -- and requires each site to be
classified in :data:`_REVIEWED_PERSISTENCE`. When a new store (or a new write
site) appears unclassified, the gate fails: the author must decide whether the
new file needs the versioned-delta migration contract
(``docs/design/persistence-and-migration.md``) or is exempt, and record that
decision here.

This is what keeps the contract from silently eroding: it is impossible to add
a persisted file without consciously classifying it.

Classifications (see :data:`_CLASSIFICATIONS`):

* ``versioned``        -- carries a schema/epoch stamp + migration (the contract).
* ``framework``        -- the persistence/migration machinery itself.
* ``secret``           -- secrets via the credential store; no JSON schema concern.
* ``export``           -- user-initiated write to a chosen/output file, not a store.
* ``content``          -- user-created data; shape is additive/self-describing, no
                          "changed default" problem.
* ``cache``            -- regenerable recency/usage/log; loss is harmless.
* ``marker``           -- a small boolean/state flag, trivially defaulted.
* ``needs-versioning`` -- real user *config* that should adopt the contract but has
                          not yet. The tracked backlog; not a free pass.
"""

from __future__ import annotations

import ast
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]

_PERSIST_CALLEE = "write_json_atomic"

_CLASSIFICATIONS: dict[str, str] = {
    "versioned": "Schema/epoch stamped with a migration path (the contract).",
    "framework": "Part of the persistence/migration machinery itself.",
    "secret": "Secret stored via the credential store; no JSON-schema migration concern.",
    "export": "User-initiated export/output to a chosen file, not a persistent store.",
    "content": "User-created data; shape is additive/self-describing (no changed-default risk).",
    "cache": "Regenerable recency/usage/log data; loss is harmless.",
    "marker": "A small boolean/state marker, trivially defaulted.",
    "needs-versioning": "Real user config that should adopt the versioned contract (backlog).",
}

#: Every ``write_json_atomic`` site -> its classification. Keep in sync with the
#: source (the gate fails otherwise). ``needs-versioning`` entries are the
#: prioritized backlog to route through ``versioned_store``.
_REVIEWED_PERSISTENCE: dict[str, str] = {
    # --- versioned (the contract) ---
    "core/settings.py::save_settings": "versioned",
    "core/keymap.py::save_keymap": "versioned",
    "core/keymap.py::load_keymap": "versioned",
    "core/features.py::save": "versioned",
    "core/custom_profiles.py::save_custom_profiles": "versioned",
    "core/mastodon/accounts.py::_persist": "versioned",
    # --- framework / migration machinery ---
    "core/versioned_store.py::load_with_migration": "framework",
    "core/migration_backup.py::backup_before_migration": "framework",
    "core/startup_maintenance.py::run_pending_startup_maintenance": "framework",
    "core/data_location.py::_write_migration_notice": "framework",
    "core/data_location.py::decline_legacy_data_import": "framework",
    "core/data_location.py::request_data_location_change": "framework",
    "core/data_location.py::request_legacy_data_import": "framework",
    "core/storage_mode.py::save_storage_mode": "framework",
    "core/recovery.py::_save_state": "framework",
    "core/speech/dictation/recovery.py::save_metadata": "framework",
    # --- export / output (user picks the file) ---
    "core/keymap.py::export_keyboard_pack": "export",
    "core/keymap.py::export_keymap": "export",
    "core/features.py::export_feature_profile_file": "export",
    "core/share_package.py::write_package_file": "export",
    "core/speech/batch_manifest.py::write_manifest": "export",
    "core/speech/job_file.py::save_job": "export",
    "core/brf_sidecar.py::write_sidecar": "export",
    "io/illumination.py::write_illumination": "export",
    # --- secret (credential store) ---
    "core/assistant_ai.py::save_assistant_api_key": "secret",
    "platform/windows/credential_store.py::_write_store": "secret",
    "core/remote_sites.py::save_password": "secret",
    "core/remote_sites.py::delete_password": "secret",
    "core/publishing.py::save_publishing_secret": "secret",
    # --- cache / recency / log (regenerable) ---
    # Audio Studio: saved SFTP destinations and the folder feed's show settings
    # are user-created, additive-shaped stores; the listening position and the
    # incremental-rebuild fingerprints are regenerable.
    # A list of catalogue addresses the user chose to add. Additive and
    # self-describing: an unknown key is ignored on read and a built-in that
    # is not in the file keeps its shipped default, so a newer build adding a
    # field cannot change what an older one already searches.
    # This machine's sync settings: a folder, a device label, two switches.
    # Additive and self-describing, and never the recovery phrase -- that is
    # a key and lives in the platform credential store.
    "core/sync/places_config.py::save": "content",
    # Quill Radio download preferences: a root folder and four filing
    # switches. Additive and self-describing; a damaged file reads as the
    # defaults, which is where every install starts anyway.
    # Where each remembered file was last seen on *this* machine. A cache in
    # the strict sense: a stale entry is dropped on read, losing it costs a
    # row in a list, and it is deliberately never synced.
    "core/media/local_paths.py::remember": "cache",
    "core/media/local_paths.py::forget": "cache",
    "core/radio/download_prefs.py::save": "content",
    "core/library/catalogs.py::save": "content",
    "core/publish/destinations.py::save_destinations": "content",
    "core/publish/feed_folder.py::save_feed_config": "content",
    # Audio Studio Phase 2 (standalone port-in): per-book volume/mute prefs,
    # the user's book library (folders/favorites), the Recently Played history,
    # the play queue, and the sleep timer setting -- all user-created,
    # additive-shaped stores with tolerant loaders (a corrupt file degrades to
    # empty/default), same shape as the radio/podcasts stores above.
    "core/audio_studio/book_prefs.py::save_prefs": "content",
    "core/audio_studio/history.py::save_history": "content",
    "core/audio_studio/library.py::save_library": "content",
    "core/audio_studio/play_queue.py::save_queue": "content",
    "core/audio_studio/sleep_timer.py::save_sleep_setting": "content",
    # Component refcounts: which installed apps still need each shared component.
    # Regenerable -- each app re-asserts its REQUIRED_COMPONENTS on launch -- so
    # loss is self-healing, not user data.
    "core/components.py::_save": "cache",
    # QuillVille companion apps (Quill Radio/Weather/Cast) + shared runtime.
    # app_features and the weather monitor config are user choices with tolerant
    # loaders (a corrupt file degrades to all-on / defaults), same shape as the
    # radio/podcasts content stores. The runtime marker/refs and the monitor's
    # already-notified id set are regenerable machinery: the marker is re-dropped
    # by the installer, refcounts are re-asserted by each app on launch, and a
    # lost notified-id set at worst re-announces an alert already seen.
    "core/app_features.py::save_app_features": "content",
    "core/weather/monitor.py::save_config": "content",
    "core/runtime_marker.py::write_marker": "framework",
    "core/runtime_refs.py::_save": "cache",
    "core/weather/monitor.py::save_notified_ids": "cache",
    "core/radio/favorites.py::save_favorites": "content",
    # --- 2026-08-21: the Choose Columns / chapters / Listening Places wave ---
    # Which columns a list speaks and in what order, per surface. A user choice
    # with real structure (order plus a hidden set), an additive shape and a
    # tolerant loader: an unknown column id is dropped on read and a corrupt
    # file degrades to the app's catalogue defaults, which is where every
    # install starts. Same store shape as quick_actions, deliberately.
    "core/media/list_columns.py::save_column_layouts": "content",
    # The user-ordered action list per content type, whose first entry is the
    # default for Enter. Same reasoning as list_columns above.
    "core/quick_actions.py::save_quick_actions": "content",
    # An observed log of what was played and for how long, behind Listening
    # Stats and Year in Review. Not user-authored, capped by a retention
    # window, rebuilt as you listen: losing it costs the report, not the
    # library. Same call as radio/song_history.py.
    "core/media_stats.py::save_sessions": "cache",
    # Radio -> Cast instruction handoff: "play next", "add to queue", "send to
    # the Inbox", written by Radio and consumed by Cast at merge. The exact
    # counterpart of radio_listens (which carries what Radio *heard*) and
    # classified the same way: loss means one instruction is missed, which is
    # why an older Cast that never opens the file leaves it waiting rather than
    # consuming it.
    "core/podcasts/radio_actions.py::record_action": "cache",
    "core/podcasts/radio_actions.py::merge_radio_actions": "cache",
    # Listening Places (spec listening-places/1): this device's file in a
    # folder any podcast app may read and write. User data, and the one entry
    # here whose shape is NOT ours alone to change -- the format is published,
    # with JSON conformance fixtures both implementations test against, so a
    # field may be added but never repurposed. Every device writes exactly one
    # file and reads everyone else's, which is what stops a cloud drive
    # producing a conflicted copy.
    "core/sync/listening_places.py::write_device_file": "content",
    "core/radio/history.py::save_history": "content",
    # An observed log of what each station played, not user-authored config:
    # every field is additive with a tolerant loader, there is no default whose
    # meaning could silently change, and losing it costs only the "what was that
    # song earlier?" record. Capped per station and rebuilt as you listen.
    "core/radio/song_history.py::save_song_history": "cache",
    # Chapters worked out from a transcript or an audio scan, kept so the
    # expensive tiers run once. Regenerable by definition -- deleting it costs
    # only the recompute -- and it is deliberately invalidated whenever the
    # audio file's size or mtime changes, so it can never outlive its episode.
    "core/podcasts/chapter_inference.py::save_cached_inference": "cache",
    # Radio -> Cast listening handoff: latest position/finished per episode,
    # consumed by Cast at merge. Loss = Cast misses one session; harmless.
    # The speed you chose for a show, remembered per feed. A preference, but a
    # trivially defaulted one: losing it plays the next episode at 1x, which is
    # where it started.
    "core/podcasts/radio_listens.py::remember_show_speed": "marker",
    # "Don't ask me again" for the confirmations that offer it (Mark All as
    # Played, and the delete prompts). A boolean per question; losing it asks
    # once more, which is the safe direction.
    "core/podcasts/ask_prefs.py::set_should_ask": "marker",
    "core/podcasts/radio_listens.py::record_listen": "cache",
    "core/podcasts/radio_listens.py::merge_radio_listens": "cache",
    # Two-machines guard for synced data folders: {machine, pid, at}.
    "core/profile_heartbeat.py::note_profile_use": "marker",
    "core/radio/wake_timer.py::save_wake_setting": "content",
    "core/radio/recording.py::save_recording_settings": "content",
    "core/radio/recording_schedule.py::save_schedule": "content",
    "core/podcasts/subscriptions.py::save_library": "content",
    "core/podcasts/history.py::save_history": "content",
    "core/podcasts/episode_notes.py::save_episode_notes": "content",
    # Quick Actions (1.1.0): the listener's own ordering of the episode,
    # podcast, and queue action lists. Content -- it is a preference they
    # arranged by hand and would notice losing -- but it self-repairs against
    # the build's known action set on every read, so a file from a newer or
    # older QUILL Cast can never strand a menu.
    "core/podcasts/quick_actions.py::save_quick_actions": "content",
    # Listening statistics (1.1.0): an append-only session log, pruned on
    # write against a 90-day retention window and hard-capped. Content: it is
    # a record of what the listener did, exportable as CSV, and losing it
    # loses history nothing else holds.
    "core/podcasts/stats.py::save_sessions": "content",
    "core/unlock_codes.py::save": "content",
    # A listening position is the LEAST reproducible thing in the media
    # stack: lose it and there is no way to recompute where somebody was in
    # a thirty-hour book. It was classified "cache" (regenerable) here,
    # which is exactly wrong -- and would have made it a candidate for any
    # future prune-the-caches sweep. The store now lives in
    # core/media/positions.py, keyed portably so it can also sync.
    "core/media/positions.py::_write": "content",
    # Quill Radio 3.0's own resume store, and content for exactly the same
    # reason as core/media/positions.py above: a place in a four-hour LibriVox
    # chapter cannot be recomputed. Deliberately a *second* store rather than a
    # reuse -- positions.py keys on a file's name and size, and nothing Radio
    # plays here is a file, so these key on the normalised stream URL. A
    # prune-the-caches sweep must never be able to take either of them.
    "core/radio/resume.py::_write": "content",
    # The servers and channels a listener added by hand. Nothing regenerates
    # them: no directory lists somebody's church or school Icecast box, which is
    # the entire reason the branch exists. Content, and small.
    "core/radio/my_servers.py::_write": "content",
    "core/radio/youtube_channels.py::_write": "content",
    # Saved YouTube playlists and single videos (the YouTube branch's shelf),
    # same shape and same reasoning as the channel store above it.
    "core/radio/youtube_saved.py::_write": "content",
    # Browse levels, cached so opening a source does not re-download its whole
    # index every time (the Xiph genre page alone is 5 MB). Regenerable by
    # definition -- every entry has a live fetch behind it -- and each answer
    # carries its own age so a stale one can say so rather than imply currency.
    "core/radio/directory_cache.py::save": "cache",
    "core/speech/synth_cache.py::save_cache": "cache",
    "core/palette.py::save_palette_usage": "cache",
    "core/recent.py::save_recent_files": "cache",
    "core/recent.py::_save_path_list": "cache",
    "core/search_history.py::add_search_term": "cache",
    "core/notifications.py::save_notifications": "cache",
    "core/notifications.py::clear_notifications": "cache",
    # Remote feature kill switch: the locally-cached set of features a signed
    # safety advisory has disabled, so the lock persists offline/across restarts.
    "core/safety/feature_lock.py::save_feature_locks": "cache",
    "core/diagnostics.py::record_diagnostic_event": "cache",
    "core/sessions.py::add_recent_session": "cache",
    "core/sessions.py::clear_recent_sessions": "cache",
    "core/watch_queue.py::_save_locked": "cache",
    "core/ai/activity_log.py::append": "cache",
    # Resumable batch-run record (#1323): regenerable model results keyed by unit
    # id so an interrupted bulk run resumes instead of restarting. It stamps its
    # own version + a run signature and drops the record wholesale on any mismatch
    # (start clean, never migrate/blend), so losing it just recomputes -- no
    # schema-migration concern.
    "core/ai/resume_record.py::_write": "cache",
    # --- marker / small state flags ---
    # Radio's active-recording resume marker (R1-R4): transient state written
    # when a recording starts and cleared on clean stop; absent by default, and
    # its loss just means no resume offer on the next launch.
    "core/radio/recording_resume.py::save_marker": "marker",
    "core/onboarding.py::mark_assistant_onboarding_complete": "marker",
    "core/onboarding.py::mark_glow_onboarding_complete": "marker",
    "core/onboarding.py::mark_onboarding_complete": "marker",
    "core/onboarding.py::mark_speech_onboarding_complete": "marker",
    "core/onboarding.py::mark_startup_wizard_prompt_suppressed": "marker",
    "core/onboarding.py::mark_trust_consent_complete": "marker",
    "core/onboarding.py::mark_watch_folder_onboarding_complete": "marker",
    "core/github/consent.py::save_github_consent_complete": "marker",
    "core/spotify/consent.py::save_spotify_consent_complete": "marker",
    "ui/main_frame.py::_maybe_run_first_run_onboarding": "marker",
    "core/ai/model_manager.py::save_ai_enabled": "marker",
    "core/ai/external_engine.py::set_external_engines_enabled": "marker",
    "core/speech/service.py::save_input_device": "marker",
    "core/ai/quick_switch.py::save_preferred_harness_id": "marker",
    "core/ai/onboarding.py::_save_state": "marker",
    # --- content (user-created data; additive) ---
    # Moved to core/abbreviations_store.py under GATE-11; the classification
    # travels with it, and the shape is unchanged (every field defaults, and
    # a field nobody set is not written).
    "core/abbreviations_store.py::save_abbreviation_library": "content",
    "core/assistant_prompts.py::save_custom_prompts": "content",
    "core/ai/custom_instructions.py::save_instructions": "content",
    "core/ai/sessions.py::save_session": "content",
    "core/ai/style.py::save_style": "content",
    "core/bookmarks.py::save": "content",
    # Per-book media time-point bookmarks (position_ms + optional label/note),
    # keyed by book. User-created, additive/self-describing, tolerant loader
    # (a corrupt file degrades to {}) -- same shape as core/bookmarks.py::save.
    "core/media/bookmarks.py::_write": "content",
    "core/clip_library.py::_save": "content",
    "core/copy_tray.py::_save": "content",
    "core/favorite_folders.py::save": "content",
    "core/header_footer_store.py::save": "content",
    # GitHub Items pinned repos + favorites (GHManage parity): local bookmarks
    # keyed by owner/repo and URL — user content, tolerant loader (unknown
    # fields ignored, corrupt file degrades to empty).
    "core/github/saved_items.py::save": "content",
    # Emoji picker recently-used + favorites: same shape and same tolerance as
    # saved_items.py above (a corrupt file degrades to empty, unknown fields
    # ignored) -- losing this list is mildly annoying, not data loss, and it
    # never affects the emoji catalog itself (a separate, read-only file).
    "core/emoji_usage.py::save": "content",
    "core/inline_notes.py::save": "content",
    "core/macros.py::save": "content",
    "core/notebook_store.py::save_notebook": "content",
    "core/story/storage.py::save_project": "content",
    "core/prompt_library.py::_save": "content",
    "core/work_persona.py::_save": "content",
    # Restore points: content-addressed document snapshots + a per-document
    # index carrying schema_version 1; entries are additive/self-describing and
    # corrupt indexes degrade to empty (tests/unit/core/test_restore_points.py).
    "core/restore_points.py::record_restore_point": "content",
    "core/restore_points.py::prune_restore_points": "content",
    "core/skill_store.py::_save_state": "content",
    "core/sessions.py::save_session": "content",
    "core/snippets.py::save_snippet_library": "content",
    "core/speech/pronunciation.py::save_dictionary": "content",
    "core/speech/project_profile.py::save_profile": "content",
    "core/sticky_notes.py::save_sticky_notes": "content",
    "core/undo_store.py::save_undo_history": "content",
    "core/spelling/session.py::undo_last": "content",
    "core/spellcheck.py::add_word_to_scope": "content",
    "core/speech/voice_blacklist.py::save_blacklist": "content",
    "core/verbosity/storage.py::save_custom": "content",
    "core/trust.py::save_trusted_locations": "content",
    # Weather locations: user-created saved places (display name, lat/lon,
    # resolved name, query) -- additive and self-describing, and a corrupt file
    # degrades to empty; content, like trust.py::save_trusted_locations above.
    "core/weather/locations.py::save_locations": "content",
    # --- needs-versioning (real config; contract adoption backlogged) ---
    # Audio Studio app-shell prefs (close-window action, etc.) written by the
    # reverse-vendored quill/apps/studio.py. Small app config with no schema
    # stamp yet -- backlogged like the other app prefs rather than mislabelled.
    "apps/studio.py::_save_app_prefs": "needs-versioning",
    # Weather settings: real user config (units, forecast/outlook counts, which
    # current-conditions details and alert severities show). It has no schema
    # stamp yet, so it is honestly backlogged to adopt the versioned contract
    # rather than mislabelled as content.
    "core/weather/settings.py::save_settings": "needs-versioning",
    # Quill Inkwell's own preferences (whether system-wide expansion is on, the
    # injection route, excluded applications, tray behaviour). Real user config
    # with no schema stamp yet, so it is honestly backlogged alongside the other
    # per-app preference stores. Note this is *not* where abbreviations live:
    # those are the shared, versioned core/abbreviations.py library.
    # --- config stores now stamped per the contract (was: needs-versioning) ---
    "core/assistant_ai.py::save_assistant_connection_settings": "versioned",
    "core/assistant_ai.py::save_provider_model": "versioned",
    "core/ai/external_engine.py::save_engine_config": "versioned",
    "core/ai/model_manager.py::save_model_choice": "versioned",
    "core/ai/model_tiers.py::_write_raw": "versioned",
    "core/publishing.py::save_publishing_connections": "versioned",
    "core/publishing_linkage.py::save_publishing_linkage_registry": "versioned",
    # Quill Inkwell's own preferences: stamped with schema_version, every
    # field defaulted individually on read, and a file from a newer build is
    # read but never written back over (which is how a preference silently
    # disappears when two machines run different builds).
    "core/expansion/settings.py::save_settings": "versioned",
    "core/quillin_settings.py::save_settings": "versioned",
    "core/quillins/loader.py::save_state": "versioned",
    "core/remote_sites.py::save_sites": "versioned",
    "core/ssh/sites.py::save_sites": "versioned",
    "core/speech/models.py::save_installed_models": "versioned",
    "core/watch_profile_store.py::_save_locked": "versioned",
    "core/menu_customization.py::save_menu_customization": "versioned",
    "core/profile_startup.py::save_profile_startup_config": "versioned",
    "ui/ai_hub_dialog.py::_save_deepgram_max_speakers": "versioned",
    "ui/main_frame_power_tools.py::toggle_read_only_guard": "versioned",
}


def _callee_name(call: ast.Call) -> str | None:
    func = call.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _enclosing_function_name(tree: ast.AST, target: ast.AST) -> str:
    best = "<module>"
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for descendant in ast.walk(node):
                if descendant is target:
                    best = node.name
    return best


def discover_persistence_sites() -> set[str]:
    """Return ``{"<rel path>::<function>"}`` for every ``write_json_atomic`` call."""
    sites: set[str] = set()
    for path in sorted(_PACKAGE_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _callee_name(node) == _PERSIST_CALLEE:
                rel = path.relative_to(_PACKAGE_ROOT).as_posix()
                sites.add(f"{rel}::{_enclosing_function_name(tree, node)}")
    return sites


def find_unreviewed_persistence() -> tuple[set[str], set[str]]:
    """Return (unreviewed_sites, stale_reviewed_entries)."""
    discovered = discover_persistence_sites()
    reviewed = set(_REVIEWED_PERSISTENCE)
    return discovered - reviewed, reviewed - discovered


def needs_versioning_backlog() -> list[str]:
    """The persisted stores still owed the versioned contract (sorted)."""
    return sorted(s for s, tag in _REVIEWED_PERSISTENCE.items() if tag == "needs-versioning")


def main() -> int:
    unreviewed, stale = find_unreviewed_persistence()
    if unreviewed:
        print("Persistence audit: unreviewed write sites (classify them in _REVIEWED_PERSISTENCE):")
        for site in sorted(unreviewed):
            print(f"  {site}")
        return 1
    print(f"Persistence audit: OK ({len(_REVIEWED_PERSISTENCE)} sites classified).")
    backlog = needs_versioning_backlog()
    if backlog:
        print(f"  needs-versioning backlog: {len(backlog)} stores")
    if stale:
        print(f"  note: {len(stale)} stale reviewed entries (renamed/removed); tidy when handy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
