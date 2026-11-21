"""Whose custom field is it: the fields Properties shows, and the ones it hides (wordpress.md 9.15).

A post's schema lists every meta key any plugin registers for REST, and some
plugins register theirs on every post type: The Events Calendar's 34 event,
venue and organizer fields arrive on an ordinary post (seen live on the test
site, 2026-11-20), burying the two or three a writer came for. Jeff decided
(2026-11-20): Properties hides **another plugin's** fields by default, with a
choice to show all of them. What stays in view:

- WordPress's own fields, and any field no known plugin owns (a theme's
  subtitle, a field the site's own code registers): QUILL cannot tell those
  apart from the site's purpose, so it never hides them;
- QUILL's own fields (QUILL Accessible Forms, QUILL Site Types);
- Yoast SEO's title, description and focus keyphrase;
- Advanced Custom Fields' field groups, which arrive under ``acf``, not here.

A hidden field is never dropped: its value stays on the site and with the
copy, and Show All Fields lists it again. Ownership is by the key's prefix,
from the plugins' own naming; a key matches the first owner whose prefix it
starts with. Wx-free.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

__all__ = [
    "KEPT_PREFIXES",
    "OTHERS_PAGE",
    "OTHER_PLUGINS",
    "hidden_sentence",
    "labelled_keys",
    "plugin_of",
    "split_keys",
]

#: The Workbench Properties page that holds them (title reviewed for a screen reader).
OTHERS_PAGE = "Fields Plugins Add to Every Item"

#: Prefixes of fields that stay in view although a plugin owns them.
KEPT_PREFIXES: tuple[str, ...] = (
    "_yoast_wpseo_",  # Yoast SEO's title, description and focus keyphrase
    "quill_",
    "_quill_",
    "qaf_",
    "_qaf_",
)

#: ``(prefix, plugin)``: the fields another plugin owns, hidden until Show All Fields.
OTHER_PLUGINS: tuple[tuple[str, str], ...] = (
    ("_Event", "The Events Calendar"),
    ("_Venue", "The Events Calendar"),
    ("_Organizer", "The Events Calendar"),
    ("_tribe_", "The Events Calendar"),
    ("_tec_", "The Events Calendar"),
    ("pmpro_", "Paid Memberships Pro"),
    ("_pmpro_", "Paid Memberships Pro"),
    ("_acf_", "Advanced Custom Fields"),  # its bookkeeping; the field groups come under acf
    ("rank_math_", "Rank Math"),
    ("_wc_", "WooCommerce"),
    ("_woocommerce_", "WooCommerce"),
    ("_gform", "Gravity Forms"),
    ("_elementor_", "Elementor"),
    ("_et_", "Divi"),
    ("_jetpack_", "Jetpack"),
    ("jetpack_", "Jetpack"),
    ("_wpcom_", "Jetpack"),
    ("_aioseo_", "All in One SEO"),
    ("_seopress_", "SEOPress"),
    ("_wpml_", "WPML"),
    ("_mc4wp_", "Mailchimp for WordPress"),
    ("_wpforms_", "WPForms"),
    ("_give_", "GiveWP"),
)


def plugin_of(key: str) -> str:
    """The other plugin that owns *key*, or "" when Properties shows it by default."""
    if key.startswith(KEPT_PREFIXES):
        return ""
    return next((name for prefix, name in OTHER_PLUGINS if key.startswith(prefix)), "")


def split_keys(keys: Iterable[str]) -> tuple[list[str], dict[str, list[str]]]:
    """``(shown, hidden by plugin)``, each in the order given."""
    shown: list[str] = []
    hidden: dict[str, list[str]] = {}
    for key in keys:
        owner = plugin_of(key)
        if owner:
            hidden.setdefault(owner, []).append(key)
        else:
            shown.append(key)
    return shown, hidden


def labelled_keys(
    keys: Iterable[str],
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """``(shown, hidden)`` as ``(key, label)``; a hidden one says whose it is, by owner."""
    shown, hidden = split_keys(keys)
    others = [(k, f"{k} ({owner})") for owner, ks in sorted(hidden.items()) for k in ks]
    return [(k, k) for k in shown], others


def hidden_sentence(hidden: Mapping[str, int]) -> str:
    """ "36 fields are hidden because a plugin adds them to every item: 34 from ..."

    Empty when nothing is hidden. The largest owner comes first, its number
    before its name, so a count is never heard as part of a plugin's name
    (accessibility review, 2026-11-20).
    """
    counts = {name: n for name, n in hidden.items() if n}
    if not counts:
        return ""
    total = sum(counts.values())
    owners = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    each = ", ".join(f"{n} from {name}" for name, n in owners)
    if total == 1:
        return f"1 field is hidden because a plugin adds it to every item: {each}."
    return f"{total} fields are hidden because a plugin adds them to every item: {each}."
