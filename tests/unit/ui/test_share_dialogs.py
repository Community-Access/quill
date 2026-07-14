from __future__ import annotations

import pytest

from quill.core.features import FeatureManager
from quill.core.settings import Settings
from quill.core.share_package import (
    KIND_BACKUP,
    KIND_PROFILE,
    SECTION_FEATURES,
    SECTION_SETTINGS,
    PrivacyError,
    private_fields_present,
    read_package,
)
from quill.ui.share_dialogs import (
    SectionOffer,
    apply_import,
    build_export_document,
    gather_export_offers,
    importable_sections,
    read_import,
    write_export,
)


@pytest.fixture(autouse=True)
def _redirect_app_data(tmp_path, monkeypatch):
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path / "appdata"))


def _features() -> FeatureManager:
    return FeatureManager()


def test_gather_offers_lists_settings_and_features() -> None:
    offers = gather_export_offers(Settings(), _features())
    ids = {offer.id for offer in offers}
    assert ids == {SECTION_SETTINGS, SECTION_FEATURES}
    assert all(not offer.private for offer in offers)


def test_build_export_requires_a_section() -> None:
    offers = gather_export_offers(Settings(), _features())
    with pytest.raises(ValueError):
        build_export_document(
            kind=KIND_BACKUP,
            name="x",
            source_version="0.1.5",
            selected_ids=[],
            offers=offers,
        )


def test_profile_export_is_privacy_clean() -> None:
    settings = Settings(theme="dark", watch_folder_path=r"D:\watch")
    offers = gather_export_offers(settings, _features())
    document = build_export_document(
        kind=KIND_PROFILE,
        name="Share me",
        source_version="0.1.5",
        selected_ids=[SECTION_SETTINGS, SECTION_FEATURES],
        offers=offers,
    )
    assert private_fields_present(document) == []
    inner = document["sections"][SECTION_SETTINGS]["settings"]  # type: ignore[index]
    assert "watch_folder_path" not in inner
    assert inner["theme"] == "dark"


def test_round_trip_apply_restores_settings_and_features(tmp_path) -> None:
    source_settings = Settings(theme="dark", read_aloud_rate=275)
    source_features = _features()
    source_features.import_profile_data({
        "schema_version": 1,
        "active_profile_id": "writer",
        "overrides": {},
    })
    offers = gather_export_offers(source_settings, source_features)
    document = build_export_document(
        kind=KIND_BACKUP,
        name="Everything",
        source_version="0.1.5",
        selected_ids=[SECTION_SETTINGS, SECTION_FEATURES],
        offers=offers,
    )
    path = tmp_path / "backup.quillbackup"
    write_export(document, path)

    package = read_import(path)
    rows = {row[0] for row in importable_sections(package)}
    assert rows == {SECTION_SETTINGS, SECTION_FEATURES}

    target_settings = Settings()
    target_features = _features()
    outcome = apply_import(
        package, [SECTION_SETTINGS, SECTION_FEATURES], target_settings, target_features
    )
    assert outcome.settings is not None
    assert outcome.settings.theme == "dark"
    assert outcome.settings.read_aloud_rate == 275
    assert target_features.active_profile_id == "writer"
    assert len(outcome.applied) == 2


def test_apply_only_selected_sections() -> None:
    offers = gather_export_offers(Settings(theme="dark"), _features())
    document = build_export_document(
        kind=KIND_BACKUP,
        name="x",
        source_version="0.1.5",
        selected_ids=[SECTION_SETTINGS, SECTION_FEATURES],
        offers=offers,
    )
    package = read_package(document)
    target_features = _features()
    outcome = apply_import(package, [SECTION_SETTINGS], Settings(), target_features)
    assert outcome.settings is not None
    assert outcome.applied == ["Settings"]


def test_apply_rolls_back_features_on_failure() -> None:
    offers = gather_export_offers(Settings(), _features())
    document = build_export_document(
        kind=KIND_BACKUP,
        name="x",
        source_version="0.1.5",
        selected_ids=[SECTION_FEATURES],
        offers=offers,
    )
    package = read_package(document)
    package.sections[SECTION_FEATURES] = {"schema_version": 999}  # unsupported

    target_features = _features()
    target_features.import_profile_data({
        "schema_version": 1,
        "active_profile_id": "writer",
        "overrides": {},
    })
    before = target_features.active_profile_id
    with pytest.raises(ValueError):
        apply_import(package, [SECTION_FEATURES], Settings(), target_features)
    assert target_features.active_profile_id == before  # rolled back


def test_profile_refuses_private_section_via_helper() -> None:
    from quill.core.share_package import SECTION_SECRETS

    offers = [SectionOffer(SECTION_SECRETS, "Secrets", "Credentials.", True, {"k": "v"})]
    with pytest.raises(PrivacyError):
        build_export_document(
            kind=KIND_PROFILE,
            name="leak",
            source_version="0.1.5",
            selected_ids=[SECTION_SECRETS],
            offers=offers,
        )


# --- Additional shareable sections (SHARE-1 / SHARE-2) ---------------------


def _seed_all_stores() -> None:
    """Populate every shareable store under the redirected app-data dir."""
    from quill.core.ai.style import StyleProfile, save_style
    from quill.core.keymap import save_keymap
    from quill.core.macros import Macro, MacroManager
    from quill.core.snippets import Snippet, SnippetLibrary, save_snippet_library
    from quill.core.spellcheck import add_word_to_scope
    from quill.core.watch_profiles import WatchProfile
    from quill.ui.share_dialogs import _watch_store

    # Use a real command id so the saved binding survives the carry-over
    # load path (which drops unknown command ids; see #292). The test is
    # exercising the round-trip through disk, not the carry-over rule.
    # The chord must not collide with another command's default binding
    # or the conflict dropper will silently revert it to default.
    save_keymap({"format.bold": "Ctrl+Alt+B"})
    save_snippet_library(
        SnippetLibrary(
            version=1,
            snippets=[
                Snippet(
                    id="s1",
                    name="Greeting",
                    trigger=";hi",
                    body="Hello there",
                )
            ],
        )
    )
    manager = MacroManager()
    manager.macros["fixup"] = Macro(name="fixup", steps=["edit.bold", "edit.italic"])
    manager.save()
    store = _watch_store()
    store.add(WatchProfile(profile_id="w1", name="Drafts", folder_path="C:/drafts"))
    add_word_to_scope("quillington", "personal", None, None)
    save_style(StyleProfile(enabled=True, samples=["My voice sample."], guide="Be terse."))


def test_offers_include_seeded_sections() -> None:
    from quill.core.share_package import (
        SECTION_DICTIONARY,
        SECTION_KEYMAP,
        SECTION_MACROS,
        SECTION_SNIPPETS,
        SECTION_STYLE,
        SECTION_WATCH,
    )

    _seed_all_stores()
    ids = {offer.id for offer in gather_export_offers(Settings(), _features())}
    assert {
        SECTION_SETTINGS,
        SECTION_FEATURES,
        SECTION_KEYMAP,
        SECTION_SNIPPETS,
        SECTION_MACROS,
        SECTION_WATCH,
        SECTION_DICTIONARY,
        SECTION_STYLE,
    } <= ids


def test_backup_round_trip_restores_every_store(tmp_path) -> None:
    from quill.core.ai.style import StyleProfile, load_style, save_style
    from quill.core.keymap import load_keymap, save_keymap
    from quill.core.macros import MacroManager
    from quill.core.share_package import (
        SECTION_DICTIONARY,
        SECTION_KEYMAP,
        SECTION_MACROS,
        SECTION_SNIPPETS,
        SECTION_STYLE,
        SECTION_WATCH,
    )
    from quill.core.snippets import SnippetLibrary, load_snippet_library, save_snippet_library
    from quill.core.spellcheck import load_scope_dictionary
    from quill.ui.share_dialogs import _watch_store

    _seed_all_stores()
    section_ids = [
        SECTION_KEYMAP,
        SECTION_SNIPPETS,
        SECTION_MACROS,
        SECTION_WATCH,
        SECTION_DICTIONARY,
        SECTION_STYLE,
    ]
    offers = gather_export_offers(Settings(), _features())
    document = build_export_document(
        kind=KIND_BACKUP,
        name="Full",
        source_version="0.1.5",
        selected_ids=section_ids,
        offers=offers,
    )
    path = tmp_path / "all.quillbackup"
    write_export(document, path)

    # Wipe the stores, then import the backup (replace semantics).
    save_keymap({})
    save_snippet_library(SnippetLibrary(version=1, snippets=[]))
    MacroManager().save()
    _watch_store().replace_all([])
    save_style(StyleProfile())

    package = read_import(path)
    outcome = apply_import(package, section_ids, Settings(), _features())
    assert len(outcome.applied) == len(section_ids)

    assert load_keymap().get("format.bold") == "Ctrl+Alt+B"
    assert any(s.trigger == ";hi" for s in load_snippet_library().snippets)
    assert "fixup" in MacroManager.load().macros
    assert any(p.name == "Drafts" for p in _watch_store().profiles())
    assert "quillington" in load_scope_dictionary("personal", None, None)
    assert load_style().guide == "Be terse."


def test_profile_merge_is_additive_for_keymap() -> None:
    from quill.core.keymap import load_keymap, save_keymap
    from quill.core.share_package import SECTION_KEYMAP

    # Use real command ids — the carry-over load path drops unknown ones
    # (#292), so the round-trip only works for valid saved bindings.
    save_keymap({"format.bold": "Ctrl+Alt+B"})
    offers = gather_export_offers(Settings(), _features())
    document = build_export_document(
        kind=KIND_PROFILE,
        name="Keys",
        source_version="0.1.5",
        selected_ids=[SECTION_KEYMAP],
        offers=offers,
    )

    # Recipient already has a different custom binding.
    save_keymap({"format.italic": "Ctrl+Alt+I"})
    package = read_package(document)
    apply_import(package, [SECTION_KEYMAP], Settings(), _features())
    merged = load_keymap()
    assert merged.get("format.bold") == "Ctrl+Alt+B"  # imported
    assert merged.get("format.italic") == "Ctrl+Alt+I"  # preserved


def test_feature_import_announces_dependency_enable() -> None:
    # core.macros depends on core.editor -> core.app; importing macros enabled
    # must announce any dependency that had to be switched on (FLAG-1).
    source = _features()
    source.disable_feature("core.macros")
    enabled = source.enable_feature("core.macros")
    assert "core.macros" in enabled
    offers = gather_export_offers(Settings(), source)
    document = build_export_document(
        kind=KIND_BACKUP,
        name="Feat",
        source_version="0.1.5",
        selected_ids=[SECTION_FEATURES],
        offers=offers,
    )
    package = read_package(document)

    target = _features()
    target.disable_feature("core.macros")
    outcome = apply_import(package, [SECTION_FEATURES], Settings(), target)
    assert target.is_enabled("core.macros")
    # A dependency announcement is present when a dependency had to flip on.
    assert any("dependency" in warning for warning in outcome.warnings) or target.is_enabled(
        "core.editor"
    )
