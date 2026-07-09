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
    "core/publish/destinations.py::save_destinations": "content",
    "core/publish/feed_folder.py::save_feed_config": "content",
    "core/speech/listening_positions.py::save_position_ms": "cache",
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
    # --- marker / small state flags ---
    "core/onboarding.py::mark_assistant_onboarding_complete": "marker",
    "core/onboarding.py::mark_glow_onboarding_complete": "marker",
    "core/onboarding.py::mark_onboarding_complete": "marker",
    "core/onboarding.py::mark_speech_onboarding_complete": "marker",
    "core/onboarding.py::mark_startup_wizard_prompt_suppressed": "marker",
    "core/onboarding.py::mark_trust_consent_complete": "marker",
    "core/onboarding.py::mark_watch_folder_onboarding_complete": "marker",
    "core/github/consent.py::save_github_consent_complete": "marker",
    "ui/main_frame.py::_maybe_run_first_run_onboarding": "marker",
    "core/ai/model_manager.py::save_ai_enabled": "marker",
    "core/ai/external_engine.py::set_external_engines_enabled": "marker",
    "core/speech/service.py::save_input_device": "marker",
    "core/ai/quick_switch.py::save_preferred_harness_id": "marker",
    "core/ai/onboarding.py::_save_state": "marker",
    # --- content (user-created data; additive) ---
    "core/abbreviations.py::save_abbreviation_library": "content",
    "core/assistant_prompts.py::save_custom_prompts": "content",
    "core/ai/custom_instructions.py::save_instructions": "content",
    "core/ai/sessions.py::save_session": "content",
    "core/ai/style.py::save_style": "content",
    "core/bookmarks.py::save": "content",
    "core/clip_library.py::_save": "content",
    "core/copy_tray.py::_save": "content",
    "core/header_footer_store.py::save": "content",
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
    # --- config stores now stamped per the contract (was: needs-versioning) ---
    "core/assistant_ai.py::save_assistant_connection_settings": "versioned",
    "core/assistant_ai.py::save_provider_model": "versioned",
    "core/ai/external_engine.py::save_engine_config": "versioned",
    "core/ai/model_manager.py::save_model_choice": "versioned",
    "core/ai/model_tiers.py::_write_raw": "versioned",
    "core/publishing.py::save_publishing_connections": "versioned",
    "core/publishing_linkage.py::save_publishing_linkage_registry": "versioned",
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
