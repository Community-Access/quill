"""qc.md X-02, X-03: recipes and profiles are visible bundles of real settings."""

from __future__ import annotations

from pathlib import Path

from quill.core import settings_recipes as sr
from quill.core.settings import Settings


def test_every_bundle_names_only_real_settings_with_their_types() -> None:
    settings = Settings()
    names = sr.known_fields(settings)
    for bundle in (*sr.RECIPES, *sr.PROFILES):
        for name, value in bundle.changes:
            assert name in names, (bundle.id, name)
            assert type(getattr(settings, name)) is type(value), (bundle.id, name)


def test_a_recipe_previews_applies_and_puts_back() -> None:
    settings = Settings()
    settings.podcast_check_audible_tick = True
    recipe = next(b for b in sr.RECIPES if b.id == "quiet_background")
    lines = sr.preview(recipe, settings)
    assert any("on becomes off" in line for line in lines)
    previous = sr.apply(recipe, settings)
    assert settings.podcast_check_audible_tick is False
    assert sr.restore(settings, previous) == len(previous)
    assert settings.podcast_check_audible_tick is True


def test_a_session_profile_is_undone_at_the_next_start(tmp_path: Path, monkeypatch) -> None:
    saved: list[Settings] = []
    monkeypatch.setattr("quill.core.settings.save_settings", saved.append)
    settings = Settings()
    focus = next(b for b in sr.PROFILES if b.id == "focus")
    settings.spellcheck_as_you_type = True
    previous = sr.apply(focus, settings)
    sr.save_state(tmp_path, {"focus": {"previous": previous, "session": True}})
    assert settings.spellcheck_as_you_type is False
    assert sr.undo_session_profiles(settings, tmp_path) == 1
    assert settings.spellcheck_as_you_type is True
    assert sr.load_state(tmp_path) == {}
    assert saved
