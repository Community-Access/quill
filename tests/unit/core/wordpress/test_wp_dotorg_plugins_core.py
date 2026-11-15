"""WP-G, wx-free: WordPress.org's plugin directory -- search, readable details, the closed
or abandoned warning, and the update and rollback limits every install preview states."""

from __future__ import annotations

import io
import json
from datetime import date
from typing import Any
from urllib.error import HTTPError

from quill.core.wordpress import dotorg
from quill.core.wordpress.workbench_no_rest import PLUGIN_RECOVERY

TODAY = date(2026, 11, 13)


class _Answer(io.BytesIO):
    def __enter__(self) -> _Answer:
        return self

    def __exit__(self, *_a: Any) -> None:
        self.close()


def _akismet(**more: Any) -> dict[str, Any]:
    return {
        "slug": "akismet",
        "name": "Akismet Anti-spam",
        "version": "5.3",
        "author": '<a href="https://automattic.com">Automattic</a>',
        "rating": 92,
        "num_ratings": 1000,
        "active_installs": 5000000,
        "last_updated": "2026-10-01 3:45pm GMT",
        "tested": "6.8.1",
        "requires": "5.8",
        "requires_php": False,
        "short_description": "Stops spam.",
        **more,
    }


def test_plugin_search_sends_only_the_words_and_says_each_plugin_in_words() -> None:
    asked: list[str] = []

    def door(request: Any, timeout: float = 0) -> Any:
        asked.append(request.full_url)
        return _Answer(json.dumps({"plugins": [_akismet()]}).encode())

    found = dotorg.search_plugins("stop spam", opener=door)
    assert asked[0].startswith("https://api.wordpress.org/plugins/info/1.2/?action=query_plugins")
    assert "stop+spam" in asked[0]
    assert found[0].sentence(TODAY, describe=True) == (
        "Akismet Anti-spam, version 5.3, by Automattic, rated 4.6 of 5 by 1000 people, "
        "5,000,000+ active installs, last updated 2026-10-01, tested up to WordPress 6.8.1, "
        "needs WordPress 5.8. Stops spam."
    )
    assert dotorg.search_plugins("  ", opener=door) == []
    assert len(asked) == 1


def test_a_plugin_not_updated_in_two_years_is_said_to_be_maybe_abandoned() -> None:
    old = dotorg.parse_plugin(_akismet(last_updated="2023-05-01 1:00pm GMT"))
    assert old is not None
    assert "since 2023-05-01, over two years: it may be abandoned" in old.warning(TODAY)
    assert "Warning: " in old.sentence(TODAY)
    fresh = dotorg.parse_plugin(_akismet())
    assert fresh is not None and fresh.warning(TODAY) == ""


def test_details_read_a_closed_plugin_from_its_404_and_an_unknown_one_as_none() -> None:
    asked: list[str] = []
    closed = {
        "error": "closed",
        "name": "Old Forms",
        "slug": "old-forms",
        "closed": True,
        "closed_date": "2024-02-03",
        "reason_text": "Security Issue",
    }

    def door(request: Any, timeout: float = 0) -> Any:
        asked.append(request.full_url)
        if "old-forms" in request.full_url:
            raise HTTPError(
                request.full_url, 404, "Not Found", {}, io.BytesIO(json.dumps(closed).encode())
            )
        if "my-custom" in request.full_url:
            raise HTTPError(
                request.full_url, 404, "Not Found", {}, io.BytesIO(b'{"error":"Plugin not found."}')
            )
        return _Answer(json.dumps(_akismet()).encode())

    slugs = [dotorg.plugin_slug(p) for p in ("akismet/akismet", "old-forms/forms", "my-custom.php")]
    assert slugs == ["akismet", "old-forms", "my-custom"]
    found = dotorg.plugin_details([*slugs, "akismet"], opener=door)
    assert len(asked) == 3 and all("action=plugin_information" in url for url in asked)
    assert found["my-custom"] is None
    gone = found["old-forms"]
    assert gone is not None and gone.closed
    assert gone.sentence(TODAY) == (
        "WordPress.org closed Old Forms on 2024-02-03 (Security Issue): it gets no updates "
        "there and cannot be installed from it."
    )
    assert "not in the WordPress.org directory" in dotorg.not_listed_sentence("My Custom")


def test_the_rollback_limit_names_the_only_recovery() -> None:
    assert "no rollback" in PLUGIN_RECOVERY
    assert "deactivating or deleting" in PLUGIN_RECOVERY


def test_the_new_plugin_commands_have_help_and_a_written_reason_for_no_chord() -> None:
    from quill.core.wordpress.workbench_actions import WINDOW_MENU, WORDPRESS_ACTIONS
    from quill.core.wordpress.workbench_admin_actions import KEYLESS, command
    from quill.core.workbench.menus import rows

    bound = {row.command_id for _menu, row in rows(WINDOW_MENU)}
    offered = {a.command_id: a for a in WORDPRESS_ACTIONS.rows_for("plugin")}
    for verb in ("plugin_directory", "find_plugin"):
        action = offered[command(verb)]
        assert action.help, verb
        assert command(verb) in bound or KEYLESS.get(command(verb)), verb
