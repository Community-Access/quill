"""Every WordPress Workbench command says how much it changes (how.md review 1).

The access check reads a command's tier; a command with none used to pass
unchecked. ``tier_of`` answers for every handler the provider has, so a new
command fails here until it is classified.
"""

from __future__ import annotations

import pytest

from quill.core.wordpress.workbench_actions import WORDPRESS_ACTIONS, command
from quill.core.wordpress.workbench_tiers import MENU_TIERS, effective_command, tier_of
from quill.core.workbench.actions import Tier

pytest.importorskip("wx")


def test_every_handler_has_a_tier() -> None:
    from quill.ui.wordpress_workbench_window import WordPressWorkbenchProvider

    verbs = sorted(name[3:] for name in dir(WordPressWorkbenchProvider) if name.startswith("do_"))
    missing = [v for v in verbs if tier_of(command(v), WORDPRESS_ACTIONS) is None]
    assert missing == [], "classify these in quill/core/wordpress/workbench_tiers.py"


def test_menu_bar_writes_are_not_reads() -> None:
    assert tier_of(command("empty_spam"), WORDPRESS_ACTIONS) is Tier.DESTRUCTIVE
    assert tier_of(command("import_posts"), WORDPRESS_ACTIONS) is Tier.WRITE
    assert tier_of(command("new_here"), WORDPRESS_ACTIONS) is Tier.WRITE  # a node's row
    assert tier_of(command("roles"), WORDPRESS_ACTIONS) is Tier.READ
    for command_id in MENU_TIERS:  # none is also a context-menu row with another tier
        assert not WORDPRESS_ACTIONS.row_types_offering(command_id), command_id


def test_delete_and_shift_delete_are_checked_as_what_they_run() -> None:
    assert effective_command(command("trash"), "user") == command("remove_user")
    assert effective_command(command("delete_permanently"), "user") == command("remove_user")
    assert effective_command(command("trash"), "app_password") == command("revoke")
    assert effective_command(command("delete_permanently"), "app_password") == command("revoke")
    assert effective_command(command("trash"), "shop_product") == command("trash_product")
    assert effective_command(command("trash"), "item") == command("trash")
    assert effective_command(command("reply"), "user") == command("reply")
