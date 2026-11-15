"""The Practice Site's lesson material: written only into its own folder, and taken away again."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.wordpress import workbench_practice_material as material
from quill.core.wordpress.workbench_practice import practice_dir


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    """A Practice Site that has been started once: it has a WordPress folder."""
    site = practice_dir(tmp_path)
    (site / "wordpress").mkdir(parents=True)
    (site / "wordpress" / "wp-load.php").write_bytes(b"<?php\n")
    return site


def _written(folder: Path) -> set[str]:
    return {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}


def test_a_site_never_started_has_nowhere_to_put_it(tmp_path: Path) -> None:
    site = practice_dir(tmp_path)
    assert "Start the Practice Site once first" in material.missing_site_words(site)
    with pytest.raises(RuntimeError):
        material.set_up(site)
    assert not site.exists()


def test_set_up_writes_the_plugins_and_the_material_inside_the_site_only(folder: Path) -> None:
    before = _written(folder)
    said = material.set_up(folder)
    added = _written(folder) - before
    assert added == {
        "wordpress/wp-content/mu-plugins/quill-practice-lessons.php",
        "wordpress/wp-content/plugins/quill-practice-countdown/quill-practice-countdown.php",
        "wordpress/wp-content/plugins/quill-practice-countdown-plus/"
        "quill-practice-countdown-plus.php",
        "lesson-material.json",
    }
    assert material.is_set_up(folder)
    assert "broken link" in said and "F5" in said
    php = (folder / "wordpress" / material.MATERIAL_PLUGIN).read_text(encoding="utf-8")
    assert "define('QUILL_LESSONS_MODE', 'set')" in php
    # Runs once, and marks everything it adds so Take Away removes exactly that.
    assert "get_option('quill_practice_lessons') === '1'" in php
    assert php.count("quill_lessons_mark(") >= 5
    # The four broken things and the extras the other lessons use.
    for needle in (
        "bake-sale-table.png",
        "/our-old-address/",
        "'contcat-us'",
        "'comment_approved' => 'spam'",
        "register_post_type('practice_event'",
        "register_post_meta('practice_event', 'event_date'",
        "activate_plugin($plugin)",
        "wp_create_nav_menu('Practice Menu')",
    ):
        assert needle in php, needle
    # It names no address of its own: links are built from the site's own home_url.
    assert "http" not in php.replace("home_url", "")


def test_the_two_plugins_fight_and_site_health_says_so(folder: Path) -> None:
    plus = material.plugin_php("quill-practice-countdown-plus")
    first = material.plugin_php("quill-practice-countdown")
    assert "add_shortcode('countdown'" in plus and "add_shortcode('countdown'" in first
    # The route the Workbench's Site Health reads (wp-site-health/v1/tests/<name>).
    assert "register_rest_route('wp-site-health/v1', '/tests/practice-plugin-conflict'" in plus
    assert "'status' => $both ? 'critical' : 'good'" in plus
    with pytest.raises(ValueError):
        material.plugin_php("anything-else")


def test_take_away_writes_the_clear_mode_and_forgets_the_marker(folder: Path) -> None:
    material.set_up(folder)
    said = material.take_away(folder)
    assert not material.is_set_up(folder)
    php = (folder / "wordpress" / material.MATERIAL_PLUGIN).read_text(encoding="utf-8")
    assert "define('QUILL_LESSONS_MODE', 'clear')" in php
    assert "deactivate_plugins(" in php and "@unlink(__FILE__)" in php
    assert "'meta_key' => '_quill_lesson'" in php
    assert "wp_delete_nav_menu($menu)" in php
    assert "going" in said


def test_the_preview_lists_every_piece_and_how_to_undo(folder: Path) -> None:
    for name, what in material.MATERIAL:
        assert f"{name}: {what}" in material.PREVIEW
    assert "Take Away the Lesson Material" in material.PREVIEW
    assert "Ctrl+Z" in material.PREVIEW
    assert "real sites are not touched" in material.PREVIEW
    with pytest.raises(ValueError):
        material.material_php("maybe")


def test_files_are_written_lf(folder: Path) -> None:
    material.set_up(folder)
    for path in folder.rglob("*.php"):
        assert b"\r\n" not in path.read_bytes(), path
