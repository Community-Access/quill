"""Portable profile / backup export and import helpers (SHARE-1, SHARE-2).

This module lives in the UI layer because it composes user-facing export and
import flows, but it imports only :mod:`quill.core` and never ``wx`` so the
whole export/import pipeline stays unit-testable without a display.  The
wxPython dialogs in :mod:`quill.ui.main_frame` are thin shells over the
functions defined here.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.ai.style import StyleProfile, load_style, save_style
from quill.core.features import FeatureManager
from quill.core.keymap import DEFAULT_KEYMAP, load_keymap, merge_keymaps, save_keymap
from quill.core.macros import Macro, MacroManager
from quill.core.settings import Settings
from quill.core.settings_registry import export_settings, import_settings
from quill.core.share_package import (
    SECTION_DICTIONARY,
    SECTION_FEATURES,
    SECTION_KEYMAP,
    SECTION_MACROS,
    SECTION_SETTINGS,
    SECTION_SNIPPETS,
    SECTION_STYLE,
    SECTION_WATCH,
    Package,
    SectionSpec,
    build_package,
    read_package_file,
    section_spec,
    write_package_file,
)
from quill.core.snippets import (
    SnippetLibrary,
    load_snippet_library,
    save_snippet_library,
    snippet_library_from_dict,
)
from quill.core.spellcheck import add_word_to_scope, load_scope_dictionary
from quill.core.watch_profile_store import WatchProfileStore
from quill.core.watch_profiles import WatchProfile

#: Import merge strategies.  A shared *profile* layers onto whatever the
#: recipient already has (additive, non-destructive); a full *backup* restores
#: an exact snapshot, replacing the corresponding stores.
MODE_MERGE = "merge"
MODE_REPLACE = "replace"


def _spec(section_id: str) -> SectionSpec:
    spec = section_spec(section_id)
    if spec is None:  # pragma: no cover - section ids are module constants
        raise KeyError(section_id)
    return spec


def _watch_store() -> WatchProfileStore:
    from quill.core.paths import app_data_dir

    path = app_data_dir() / "watch" / "watch-profiles.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return WatchProfileStore(storage_path=path)


# --- Section serializers (read each store from disk for export) -------------
#
# Each loader returns the section payload, or ``None`` when the user has no
# content for that section so an empty section is never offered.


def _load_keymap_section() -> dict[str, str] | None:
    keymap = load_keymap()
    # ``load_keymap`` always returns the full resolved map; only offer it when
    # the user has actually customized a binding away from the defaults.
    if not keymap or keymap == merge_keymaps({}):
        return None
    return keymap


def _load_snippets_section() -> dict[str, object] | None:
    library = load_snippet_library()
    if not library.snippets:
        return None
    return library.to_dict()


def _load_macros_section() -> dict[str, object] | None:
    manager = MacroManager.load()
    if not manager.macros:
        return None
    return {
        "macros": {name: {"steps": list(macro.steps)} for name, macro in manager.macros.items()},
    }


def _load_watch_section() -> dict[str, object] | None:
    profiles = _watch_store().profiles()
    if not profiles:
        return None
    return {"schema_version": 1, "profiles": [profile.to_dict() for profile in profiles]}


def _load_dictionary_section() -> dict[str, object] | None:
    words = sorted(load_scope_dictionary("personal", None, None))
    if not words:
        return None
    return {"words": words}


def _load_style_section() -> dict[str, object] | None:
    profile = load_style()
    if not profile.samples and not profile.guide:
        return None
    return profile.to_dict()


#: Sections (beyond settings and features) that QUILL can serialize from the
#: live stores.  ``(section_id, loader)`` pairs.
_SECTION_LOADERS: tuple[tuple[str, Callable[[], object | None]], ...] = (
    (SECTION_KEYMAP, _load_keymap_section),
    (SECTION_SNIPPETS, _load_snippets_section),
    (SECTION_MACROS, _load_macros_section),
    (SECTION_WATCH, _load_watch_section),
    (SECTION_DICTIONARY, _load_dictionary_section),
    (SECTION_STYLE, _load_style_section),
)


@dataclass(frozen=True, slots=True)
class SectionOffer:
    """A section the user may include when exporting."""

    id: str
    title: str
    summary: str
    private: bool
    payload: object


@dataclass(slots=True)
class ImportOutcome:
    """The result of applying selected sections from a package."""

    settings: Settings | None = None
    warnings: list[str] = field(default_factory=list)
    applied: list[str] = field(default_factory=list)


def gather_export_offers(settings: Settings, features: FeatureManager) -> list[SectionOffer]:
    """Collect the sections currently available to export.

    Settings and the feature profile are always offered.  Each additional
    store (keymap, snippets, macros, watch profiles, personal dictionary, and
    writing-style model) is offered only when the user actually has content for
    it, so an empty section is never written into a package.
    """
    offers: list[SectionOffer] = []

    def _add(section_id: str, payload: object) -> None:
        spec = _spec(section_id)
        offers.append(
            SectionOffer(
                id=spec.id,
                title=spec.title,
                summary=spec.summary,
                private=spec.private,
                payload=payload,
            )
        )

    _add(SECTION_SETTINGS, export_settings(settings))
    _add(SECTION_FEATURES, features.export_profile_data())
    for section_id, loader in _SECTION_LOADERS:
        payload = loader()
        if payload is None:
            continue
        _add(section_id, payload)
    return offers


def build_export_document(
    *,
    kind: str,
    name: str,
    source_version: str,
    selected_ids: list[str] | set[str],
    offers: list[SectionOffer],
) -> dict[str, object]:
    """Build a package document from the chosen offers."""
    chosen = set(selected_ids)
    sections = {offer.id: offer.payload for offer in offers if offer.id in chosen}
    if not sections:
        raise ValueError("Choose at least one section to include.")
    return build_package(
        kind=kind,
        name=name,
        source_version=source_version,
        sections=sections,
    )


def write_export(document: dict[str, object], path: str | Path) -> None:
    """Write a built package document to disk."""
    write_package_file(document, Path(path))


def read_import(path: str | Path) -> Package:
    """Read and validate a package from disk."""
    return read_package_file(Path(path))


def importable_sections(package: Package) -> list[tuple[str, str, str]]:
    """Return ``(id, title, summary)`` for every section QUILL can apply."""
    rows: list[tuple[str, str, str]] = []
    for section_id in package.sections:
        if section_id not in _APPLIERS:
            continue
        spec = _spec(section_id)
        rows.append((spec.id, spec.title, spec.summary))
    return rows


def apply_import(
    package: Package,
    selected_ids: list[str] | set[str],
    settings: Settings,
    features: FeatureManager,
) -> ImportOutcome:
    """Apply the selected sections, rolling back features on any failure.

    The merge strategy follows the package kind: a *profile* layers onto the
    recipient's existing stores (additive) while a *backup* restores an exact
    snapshot (replace).  A snapshot of the feature state is taken before any
    change so a partial failure leaves the manager untouched.  Settings are
    returned as a new :class:`Settings` rather than mutated, so the caller
    controls persistence.  After a feature import, any feature switched on to
    satisfy a dependency is announced (FLAG-1).
    """
    chosen = set(selected_ids)
    mode = MODE_MERGE if package.is_profile else MODE_REPLACE
    outcome = ImportOutcome(settings=None)
    feature_snapshot = features.export_profile_data()
    try:
        for section_id in package.sections:
            if section_id not in chosen or section_id not in _APPLIERS:
                continue
            _APPLIERS[section_id](package, settings, features, outcome, mode)
    except Exception:
        # Restore the feature manager to its pre-import state.
        features.import_profile_data(feature_snapshot)
        raise
    return outcome


def _enabled_feature_ids(features: FeatureManager) -> set[str]:
    from quill.core.features import FEATURE_DEFINITIONS

    return {fid for fid in FEATURE_DEFINITIONS if features.is_enabled(fid)}


def _apply_settings(
    package: Package,
    _settings: Settings,
    _features: FeatureManager,
    outcome: ImportOutcome,
    _mode: str,
) -> None:
    payload = package.sections[SECTION_SETTINGS]
    outcome.settings = import_settings(payload)
    outcome.applied.append(_spec(SECTION_SETTINGS).title)


def _apply_features(
    package: Package,
    _settings: Settings,
    features: FeatureManager,
    outcome: ImportOutcome,
    _mode: str,
) -> None:
    payload = package.sections[SECTION_FEATURES]
    before = _enabled_feature_ids(features)
    outcome.warnings.extend(features.import_profile_data(payload))
    # FLAG-1: report any feature switched on to satisfy a dependency so the
    # change is never silent.
    from quill.core.features import FEATURE_DEFINITIONS

    newly_enabled = sorted(_enabled_feature_ids(features) - before)
    requested = payload.get("overrides", {}) if isinstance(payload, dict) else {}
    for feature_id in newly_enabled:
        if isinstance(requested, dict) and requested.get(feature_id) == "on":
            continue  # directly requested, not a dependency side-effect
        title = FEATURE_DEFINITIONS[feature_id].name
        outcome.warnings.append(f"Enabled {title} to satisfy a feature dependency.")
    outcome.applied.append(_spec(SECTION_FEATURES).title)


def _apply_keymap(
    package: Package,
    _settings: Settings,
    _features: FeatureManager,
    outcome: ImportOutcome,
    mode: str,
) -> None:
    payload = package.sections[SECTION_KEYMAP]
    if not isinstance(payload, dict):
        raise ValueError("Keymap section must be a mapping.")
    # The export payload is the full resolved map; only the entries that
    # actually differ from the default are the user's overrides. Without
    # this filter, importing a profile would overwrite the recipient's
    # own overrides back to the defaults the exporter happens to ship.
    incoming = {str(k): str(v) for k, v in payload.items() if str(v) != DEFAULT_KEYMAP.get(str(k))}
    if mode == MODE_MERGE:
        merged = {**load_keymap(), **incoming}
        save_keymap(merged)
    else:
        save_keymap(incoming)
    outcome.applied.append(_spec(SECTION_KEYMAP).title)


def _apply_snippets(
    package: Package,
    _settings: Settings,
    _features: FeatureManager,
    outcome: ImportOutcome,
    mode: str,
) -> None:
    library = snippet_library_from_dict(package.sections[SECTION_SNIPPETS])
    if mode == MODE_MERGE:
        existing = load_snippet_library()
        by_id = {snippet.id: snippet for snippet in existing.snippets}
        for snippet in library.snippets:
            by_id[snippet.id] = snippet  # incoming wins on id collision
        merged = sorted(by_id.values(), key=lambda item: item.name.lower())
        save_snippet_library(SnippetLibrary(version=existing.version, snippets=merged))
    else:
        save_snippet_library(library)
    outcome.applied.append(_spec(SECTION_SNIPPETS).title)


def _apply_macros(
    package: Package,
    _settings: Settings,
    _features: FeatureManager,
    outcome: ImportOutcome,
    mode: str,
) -> None:
    payload = package.sections[SECTION_MACROS]
    raw = payload.get("macros", {}) if isinstance(payload, dict) else {}
    incoming: dict[str, Macro] = {}
    if isinstance(raw, dict):
        for name, body in raw.items():
            if not isinstance(name, str) or not isinstance(body, dict):
                continue
            steps = body.get("steps", [])
            if not isinstance(steps, list):
                continue
            incoming[name] = Macro(
                name=name,
                steps=[str(step) for step in steps if isinstance(step, str) and step],
            )
    manager = MacroManager.load() if mode == MODE_MERGE else MacroManager()
    for name, macro in incoming.items():
        manager.macros[name] = macro
    manager.save()
    outcome.applied.append(_spec(SECTION_MACROS).title)


def _apply_watch(
    package: Package,
    _settings: Settings,
    _features: FeatureManager,
    outcome: ImportOutcome,
    mode: str,
) -> None:
    payload = package.sections[SECTION_WATCH]
    raw = payload.get("profiles", []) if isinstance(payload, dict) else []
    incoming = [WatchProfile.from_dict(entry) for entry in raw if isinstance(entry, dict)]
    store = _watch_store()
    if mode == MODE_REPLACE:
        store.replace_all(incoming)
    else:
        existing_ids = {profile.profile_id for profile in store.profiles()}
        for profile in incoming:
            if profile.profile_id in existing_ids:
                continue
            store.add(profile)
    outcome.applied.append(_spec(SECTION_WATCH).title)


def _apply_dictionary(
    package: Package,
    _settings: Settings,
    _features: FeatureManager,
    outcome: ImportOutcome,
    _mode: str,
) -> None:
    # Personal dictionary import is always additive (non-destructive) because
    # losing learned words would be surprising; there is no public "forget all"
    # path, so both profile and backup merge the incoming words.
    payload = package.sections[SECTION_DICTIONARY]
    words = payload.get("words", []) if isinstance(payload, dict) else []
    if isinstance(words, list):
        for word in words:
            if isinstance(word, str) and word.strip():
                add_word_to_scope(word, "personal", None, None)
    outcome.applied.append(_spec(SECTION_DICTIONARY).title)


def _apply_style(
    package: Package,
    _settings: Settings,
    _features: FeatureManager,
    outcome: ImportOutcome,
    mode: str,
) -> None:
    payload = package.sections[SECTION_STYLE]
    if not isinstance(payload, dict):
        raise ValueError("Style section must be a mapping.")
    incoming_samples = payload.get("samples", [])
    incoming = StyleProfile(
        enabled=bool(payload.get("enabled", False)),
        samples=[str(s) for s in incoming_samples if isinstance(s, str)]
        if isinstance(incoming_samples, list)
        else [],
        guide=str(payload.get("guide", "")),
    )
    if mode == MODE_REPLACE:
        save_style(incoming)
    else:
        existing = load_style()
        combined = list(existing.samples)
        for sample in incoming.samples:
            if sample not in combined:
                combined.append(sample)
        save_style(
            StyleProfile(
                enabled=existing.enabled or incoming.enabled,
                samples=combined,
                guide=incoming.guide or existing.guide,
            )
        )
    outcome.applied.append(_spec(SECTION_STYLE).title)


_APPLIERS: dict[str, Callable[[Package, Settings, FeatureManager, ImportOutcome, str], None]] = {
    SECTION_SETTINGS: _apply_settings,
    SECTION_FEATURES: _apply_features,
    SECTION_KEYMAP: _apply_keymap,
    SECTION_SNIPPETS: _apply_snippets,
    SECTION_MACROS: _apply_macros,
    SECTION_WATCH: _apply_watch,
    SECTION_DICTIONARY: _apply_dictionary,
    SECTION_STYLE: _apply_style,
}
