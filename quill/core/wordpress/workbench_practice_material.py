"""The Practice Site's lesson material: what the practice tutorials need to find (WP-R-049).

The Practice Site starts as a fresh WordPress with a welcome page, a post and
a draft. The Break It on Purpose lessons need something wrong to find, and the
spam and custom-type lessons need a held comment and an event with a field, so
Tools > Practice Site offers **Set Up the Lesson Material**, which adds:

- a picture with no alternative text, used in a post (the missing alt text);
- a post that links to an address on the site that does not exist (the broken
  link);
- two small plugins that both answer one shortcode, and a Site Health test
  that says so while both are on (the plugin conflict);
- a Contact Us page whose address is misspelt (the wrong permalink);
- a comment held as spam and one waiting for approval;
- a menu, Practice Menu, with one item, for the menus lesson;
- a Practice Events content type whose events carry an Event date field.

Nothing here talks to a network, and nothing touches any site but the one on
this computer: everything is files written into the Practice Site's own
WordPress folder (:func:`quill.core.wordpress.workbench_practice.practice_dir`),
which only that local WordPress reads. A must-use plugin does the work inside
WordPress on its next request -- at once when the site is running, since the
folder is mounted, or at its next start -- and runs only once. **Take Away the
Lesson Material** writes the same plugin in its other mode: it deletes exactly
what was added (each piece is marked), turns off and removes the two plugins,
and then removes itself. Reset, as always, removes everything. Wx-free.
"""

from __future__ import annotations

import json
from pathlib import Path

__all__ = [
    "CONFLICT_PLUGINS",
    "MATERIAL",
    "MATERIAL_PLUGIN",
    "PREVIEW",
    "TAKE_AWAY_PREVIEW",
    "is_set_up",
    "material_php",
    "missing_site_words",
    "plugin_php",
    "set_up",
    "take_away",
]

#: Where the must-use plugin lives, inside the Practice Site's WordPress folder.
MATERIAL_PLUGIN = Path("wp-content") / "mu-plugins" / "quill-practice-lessons.php"
#: The two plugins that fight over one shortcode, by folder name.
CONFLICT_PLUGINS = ("quill-practice-countdown", "quill-practice-countdown-plus")
_MARKER = "lesson-material.json"

#: What Set Up adds, one sentence each, in the order the lessons use it.
MATERIAL: tuple[tuple[str, str], ...] = (
    (
        "Missing alt text",
        "A picture called Bake sale table with no alternative text, shown in a post "
        "called Our Bake Sale.",
    ),
    (
        "Broken link",
        "A post called Where to Find Us that links to our-old-address, a page the site "
        "does not have.",
    ),
    (
        "Plugin conflict",
        "Two plugins, Practice Countdown and Practice Countdown Plus, both switched on and "
        "both answering the same shortcode; Site Health says so while both are on.",
    ),
    (
        "Wrong permalink",
        "A page called Contact Us whose address is misspelt as contcat-us.",
    ),
    (
        "Spam",
        "A comment held as spam, and a real question waiting for approval, on A First "
        "Practice Post.",
    ),
    (
        "Menu",
        "A menu called Practice Menu with one item, Home.",
    ),
    (
        "Custom type and field",
        "A Practice Events content type, with one event, Winter Concert, that has an "
        "Event date field.",
    ),
)

PREVIEW = (
    "Set up the lesson material on the Practice Site? It adds these to the WordPress on "
    "this computer only, and nothing else:\n\n"
    + "\n".join(f"{name}: {what}" for name, what in MATERIAL)
    + "\n\nTake Away the Lesson Material, in this same list, removes exactly these again, "
    "and Ctrl+Z in the list does the same. Your real sites are not touched."
)

TAKE_AWAY_PREVIEW = (
    "Take away the lesson material? This deletes the picture, posts, page, comments, menu "
    "and event the lesson material added to the Practice Site, even if you changed them, and "
    "switches off and removes the two practice plugins. Anything else you made there "
    "stays. Your real sites are not touched."
)

# A one-pixel PNG: the picture only has to exist, not to look like anything.
_PIXEL = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJ"
    "RU5ErkJggg=="
)


def _wordpress(folder: Path) -> Path:
    return folder / "wordpress"


def missing_site_words(folder: Path) -> str:
    """Why the material cannot be set up yet ("" when it can)."""
    if not (_wordpress(folder) / "wp-load.php").is_file():
        return "Start the Practice Site once first, so it has a WordPress to add the lessons to."
    return ""


def is_set_up(folder: Path) -> bool:
    """Whether Set Up has run and Take Away has not, as this computer last left it."""
    return (folder / _MARKER).is_file()


def material_php(mode: str) -> str:
    """The must-use plugin in *mode* ``"set"`` (add, once) or ``"clear"`` (remove, then itself)."""
    if mode not in ("set", "clear"):
        raise ValueError(f"mode must be set or clear, not {mode!r}")
    slugs = ", ".join(f"'{slug}/{slug}.php'" for slug in CONFLICT_PLUGINS)
    dirs = ", ".join(f"'{slug}'" for slug in CONFLICT_PLUGINS)
    return f"""<?php
/*
 * Plugin Name: QUILL Practice Lessons
 * Description: Written by QUILL for the Practice Site's lessons. In set mode it adds the
 * lesson material once; in clear mode it removes exactly that material, then itself.
 */
if (!defined('ABSPATH')) {{ exit; }}
define('QUILL_LESSONS_MODE', '{mode}');

function quill_lessons_mark($id) {{
    if ($id && !is_wp_error($id)) {{ update_post_meta($id, '_quill_lesson', '1'); }}
    return $id;
}}

function quill_lessons_types() {{
    register_post_type('practice_event', array(
        'label' => 'Practice Events',
        'labels' => array('name' => 'Practice Events', 'singular_name' => 'Practice Event'),
        'public' => true,
        'show_in_rest' => true,
        'rest_base' => 'practice-events',
        'supports' => array('title', 'editor', 'custom-fields'),
    ));
    register_post_meta('practice_event', 'event_date', array(
        'type' => 'string',
        'single' => true,
        'show_in_rest' => true,
        'description' => 'When the event happens, such as 2026-12-05 19:00.',
        'auth_callback' => function () {{ return current_user_can('edit_posts'); }},
    ));
}}

function quill_lessons_seed() {{
    if (get_option('quill_practice_lessons') === '1') {{ return; }}
    update_option('quill_practice_lessons', '1');
    $src = '';
    $picture = 0;
    $uploads = wp_upload_dir();
    if (empty($uploads['error'])) {{
        wp_mkdir_p($uploads['path']);
        $file = trailingslashit($uploads['path']) . 'bake-sale-table.png';
        file_put_contents($file, base64_decode('{_PIXEL}'));
        $picture = quill_lessons_mark(wp_insert_attachment(array(
            'post_title' => 'Bake sale table',
            'post_mime_type' => 'image/png',
            'post_status' => 'inherit',
        ), $file));
        $src = trailingslashit($uploads['url']) . 'bake-sale-table.png';
    }}
    $image = $src ? '<!-- wp:image --><figure class="wp-block-image"><img src="' . esc_url($src)
        . '"/></figure><!-- /wp:image -->' : '';
    quill_lessons_mark(wp_insert_post(array(
        'post_type' => 'post', 'post_status' => 'publish', 'post_name' => 'our-bake-sale',
        'post_title' => 'Our Bake Sale',
        'post_content' => '<!-- wp:paragraph --><p>Here is the table from last year.</p>'
            . '<!-- /wp:paragraph -->' . $image
            . '<!-- wp:shortcode -->[countdown]<!-- /wp:shortcode -->',
    )));
    quill_lessons_mark(wp_insert_post(array(
        'post_type' => 'post', 'post_status' => 'publish', 'post_name' => 'where-to-find-us',
        'post_title' => 'Where to Find Us',
        'post_content' => '<!-- wp:paragraph --><p>Directions are on <a href="'
            . esc_url(home_url('/our-old-address/')) . '">our address page</a>.</p>'
            . '<!-- /wp:paragraph -->',
    )));
    quill_lessons_mark(wp_insert_post(array(
        'post_type' => 'page', 'post_status' => 'publish', 'post_name' => 'contcat-us',
        'post_title' => 'Contact Us',
        'post_content' => '<!-- wp:paragraph --><p>Write to us any time.</p><!-- /wp:paragraph -->',
    )));
    quill_lessons_mark(wp_insert_post(array(
        'post_type' => 'practice_event', 'post_status' => 'publish',
        'post_name' => 'winter-concert', 'post_title' => 'Winter Concert',
        'post_content' => '<!-- wp:paragraph --><p>Carols and cocoa.</p><!-- /wp:paragraph -->',
        'meta_input' => array('event_date' => '2026-12-05 19:00'),
    )));
    $first = get_posts(array('name' => 'a-first-practice-post', 'post_type' => 'post',
        'post_status' => 'any', 'numberposts' => 1, 'fields' => 'ids'));
    if ($first) {{
        $spam = wp_insert_comment(array(
            'comment_post_ID' => $first[0], 'comment_author' => 'Cheap Watches Today',
            'comment_author_email' => 'deals@example.com',
            'comment_content' => 'Great post!!! Cheap watches, best prices, visit now.',
            'comment_approved' => 'spam',
        ));
        if ($spam) {{ add_comment_meta($spam, '_quill_lesson', '1'); }}
        $waiting = wp_insert_comment(array(
            'comment_post_ID' => $first[0], 'comment_author' => 'Sam Rivera',
            'comment_author_email' => 'sam@example.com',
            'comment_content' => 'Is the bake sale on Saturday or Sunday?',
            'comment_approved' => 0,
        ));
        if ($waiting) {{ add_comment_meta($waiting, '_quill_lesson', '1'); }}
    }}
    $menu = wp_create_nav_menu('Practice Menu');
    if ($menu && !is_wp_error($menu)) {{
        update_option('quill_practice_lessons_menu', (int) $menu);
        wp_update_nav_menu_item($menu, 0, array(
            'menu-item-title' => 'Home', 'menu-item-url' => home_url('/'),
            'menu-item-type' => 'custom', 'menu-item-status' => 'publish',
        ));
    }}
    require_once ABSPATH . 'wp-admin/includes/plugin.php';
    foreach (array({slugs}) as $plugin) {{
        if (is_file(WP_PLUGIN_DIR . '/' . $plugin)) {{ activate_plugin($plugin); }}
    }}
}}

function quill_lessons_clear() {{
    $ids = get_posts(array(
        'post_type' => array('post', 'page', 'attachment', 'practice_event'),
        'post_status' => array(
            'publish', 'draft', 'pending', 'private', 'future', 'inherit', 'trash',
        ),
        'numberposts' => -1, 'fields' => 'ids', 'meta_key' => '_quill_lesson',
    ));
    foreach ($ids as $id) {{
        if (get_post_type($id) === 'attachment') {{ wp_delete_attachment($id, true); }}
        else {{ wp_delete_post($id, true); }}
    }}
    $comments = get_comments(array(
        'meta_key' => '_quill_lesson', 'status' => 'any', 'fields' => 'ids',
    ));
    foreach ($comments as $comment) {{ wp_delete_comment($comment, true); }}
    $menu = (int) get_option('quill_practice_lessons_menu');
    if ($menu) {{ wp_delete_nav_menu($menu); }}
    delete_option('quill_practice_lessons_menu');
    require_once ABSPATH . 'wp-admin/includes/plugin.php';
    deactivate_plugins(array({slugs}), true);
    foreach (array({dirs}) as $slug) {{
        @unlink(WP_PLUGIN_DIR . '/' . $slug . '/' . $slug . '.php');
        @rmdir(WP_PLUGIN_DIR . '/' . $slug);
    }}
    delete_option('quill_practice_lessons');
    @unlink(__FILE__);
}}

if (QUILL_LESSONS_MODE === 'set') {{
    add_action('init', 'quill_lessons_types', 5);
    add_action('init', 'quill_lessons_seed', 20);
}} else {{
    add_action('init', 'quill_lessons_clear', 20);
}}
"""


def plugin_php(slug: str) -> str:
    """One of the two practice plugins that both answer ``[countdown]``."""
    if slug == CONFLICT_PLUGINS[0]:
        return """<?php
/*
 * Plugin Name: Practice Countdown
 * Description: Written by QUILL for a Break It on Purpose lesson on the Practice Site.
 * Shows how many days are left with [countdown].
 * Version: 1.0
 */
if (!defined('ABSPATH')) { exit; }
add_shortcode('countdown', function () { return '<p>Twelve days to go.</p>'; });
"""
    if slug == CONFLICT_PLUGINS[1]:
        first = f"{CONFLICT_PLUGINS[0]}/{CONFLICT_PLUGINS[0]}.php"
        return f"""<?php
/*
 * Plugin Name: Practice Countdown Plus
 * Description: Written by QUILL for a Break It on Purpose lesson on the Practice Site.
 * It answers [countdown] too, so it fights with Practice Countdown while both are on.
 * Version: 1.0
 */
if (!defined('ABSPATH')) {{ exit; }}
add_shortcode('countdown', function () {{
    return '<p>Countdown Plus could not start: another plugin already answers countdown.</p>';
}});

function quill_practice_conflict_result() {{
    if (!function_exists('is_plugin_active')) {{
        require_once ABSPATH . 'wp-admin/includes/plugin.php';
    }}
    $both = is_plugin_active('{first}');
    return array(
        'label' => $both ? 'Two plugins both answer the countdown shortcode'
            : 'Only one plugin answers the countdown shortcode',
        'status' => $both ? 'critical' : 'good',
        'badge' => array('label' => 'Plugins', 'color' => $both ? 'red' : 'blue'),
        'description' => $both
            ? '<p>Practice Countdown and Practice Countdown Plus are both on, and each answers '
              . 'the countdown shortcode, so a page that uses it shows the wrong words. '
              . 'Deactivate one of them.</p>'
            : '<p>Nothing to do.</p>',
        'actions' => '',
        'test' => 'practice_plugin_conflict',
    );
}}

add_action('rest_api_init', function () {{
    register_rest_route('wp-site-health/v1', '/tests/practice-plugin-conflict', array(
        'methods' => 'GET',
        'callback' => 'quill_practice_conflict_result',
        'permission_callback' => function () {{
            return current_user_can('view_site_health_checks');
        }},
    ));
}});

add_filter('site_status_tests', function ($tests) {{
    $tests['direct']['practice_plugin_conflict'] = array(
        'label' => 'Practice plugin conflict',
        'test' => 'quill_practice_conflict_result',
    );
    return $tests;
}});
"""
    raise ValueError(f"not a practice plugin: {slug!r}")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def set_up(folder: Path) -> str:
    """Write the material into the Practice Site's WordPress folder; the sentence to say.

    Raises :class:`RuntimeError` with :func:`missing_site_words` when the site
    has never been started, so there is no WordPress folder to write into.
    """
    missing = missing_site_words(folder)
    if missing:
        raise RuntimeError(missing)
    wordpress = _wordpress(folder)
    for slug in CONFLICT_PLUGINS:
        _write(wordpress / "wp-content" / "plugins" / slug / f"{slug}.php", plugin_php(slug))
    _write(wordpress / MATERIAL_PLUGIN, material_php("set"))
    _write(folder / _MARKER, json.dumps({"material": [n for n, _w in MATERIAL]}, indent=1))
    return (
        "The lesson material is on the Practice Site: a picture with no alt text, a broken "
        "link, a plugin conflict, a misspelt address, spam, a menu and a Practice Events "
        "type. "
        "Press F5 on a list to see it."
    )


def take_away(folder: Path) -> str:
    """Write the plugin in clear mode, so WordPress removes the material; the sentence to say."""
    missing = missing_site_words(folder)
    if missing:
        raise RuntimeError(missing)
    _write(_wordpress(folder) / MATERIAL_PLUGIN, material_php("clear"))
    (folder / _MARKER).unlink(missing_ok=True)
    return "The lesson material is going from the Practice Site. Press F5 on a list to check."
