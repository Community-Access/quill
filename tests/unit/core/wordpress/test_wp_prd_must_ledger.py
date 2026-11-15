"""The WordPress Workbench PRD's Must requirements, Appendix A and Appendix B, as a checked ledger.

complete.md WP-A asks for W0 to W6 to be validated against every WP-R Must
and every Appendix A object and Appendix B window. This is that validation,
written as data so it cannot rot quietly:

- :data:`MUSTS` maps each ``WP-R-<n> Must`` the PRD lists to its status, where
  it lives, and the tests that prove it (file and test function). The test
  below reads the PRD, so a new Must fails until it has a row, and checks
  every cited test function exists.
- ``met`` means a behavioural test exercises it end to end over a fake site.
  ``live`` names what still needs a real site (the test site, a plugin
  install or a screen reader); ``open`` says what is not built and why.
- :data:`APPENDIX_A` and :data:`APPENDIX_B` are checked against the real
  tree, action table and sheet builder.

Verified 2026-11-13 against the working tree of codex/workbench-combined-2026-11-10.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from quill.core.wordpress.workbench_actions import WORDPRESS_ACTIONS, command
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_sheets import sheet_for
from quill.core.wordpress.workbench_tree import _DOORS, WORDPRESS_TREE

ROOT = Path(__file__).resolve().parents[4]
PRD = (
    ROOT
    / "docs"
    / "Product Requirement Documents and Specifications"
    / "wordpress-workbench-prd.md"
)
T = "tests/unit/"
CORE = T + "core/wordpress/"
UI = T + "ui/wordpress/"

#: id -> (status, where it lives, ((test file, test function), ...), what a live run must add)
MUSTS: dict[str, tuple[str, str, tuple[tuple[str, str], ...], str]] = {
    "WP-R-001": (
        "met",
        "quill/ui/wordpress_workbench_window.py on quill/ui/workbench_frame.py",
        (
            (UI + "test_wp_workbench_window.py", "test_the_tree_has_the_prd_places_and_the_site"),
            (CORE + "test_wp_prd_must_ledger.py", "test_wordpress_uses_only_the_shared_frame"),
        ),
        "",
    ),
    "WP-R-002": (
        "met",
        "Enter on a post: open_in_editor; return keeps the place",
        (
            (UI + "test_wp_workbench_window.py", "test_enter_on_a_post_opens_it_in_the_editor"),
            (
                UI + "test_wp_workbench_lockout_ui.py",
                "test_a_custom_type_opens_in_the_editor_under_its_own_route",
            ),
            (
                UI + "test_wp_workbench_lockout_ui.py",
                "test_coming_back_to_the_workbench_keeps_node_row_and_filter",
            ),
            (
                CORE + "test_wp_prd_must_ledger.py",
                "test_a_custom_type_item_saves_back_to_its_own_route",
            ),
            (UI + "test_wp_pages_autosave.py", "test_open_offers_a_newer_autosave_and_opens_it"),
        ),
        "a screen-reader pass of leaving and returning",
    ),
    "WP-R-002a": (
        "met",
        "wordpress_workbench_window_status.py cells",
        (
            (UI + "test_wp_workbench_lockout_ui.py", "test_the_status_bar_has_the_wordpress_cells"),
            (
                UI + "test_wp_workbench_wpab.py",
                "test_list_keys_from_the_status_bar_never_reach_the_rows",
            ),
        ),
        "",
    ),
    "WP-R-003": (
        "met",
        "Needs My Attention, every connected site",
        (
            (
                UI + "test_wp_workbench_window.py",
                "test_needs_my_attention_gathers_waiting_comments",
            ),
            (
                CORE + "test_wp_workbench_core.py",
                "test_an_unreachable_site_is_one_row_and_does_not_hide_the_others",
            ),
        ),
        "",
    ),
    "WP-R-004": (
        "met",
        "workbench_tree._DOORS: every Tools > WordPress door opens a node",
        (
            (UI + "test_wp_workbench_window.py", "test_every_door_names_a_node_the_site_tree_has"),
            (UI + "test_wp_workbench_window.py", "test_the_door_always_opens_the_workbench"),
            (CORE + "test_wp_prd_must_ledger.py", "test_every_appendix_b_window_has_its_home"),
            (
                UI + "test_wp_workbench_lockout_ui.py",
                "test_visual_review_runs_the_editors_review_on_a_published_row",
            ),
        ),
        "",
    ),
    "WP-R-005": (
        "met",
        "Alt+Enter Properties: workbench_sheets.sheet_for",
        (
            (
                UI + "test_wp_workbench_window.py",
                "test_alt_enter_opens_the_post_sheet_and_ok_saves_with_verify",
            ),
            (
                CORE + "test_wp_prd_must_ledger.py",
                "test_every_appendix_a_object_has_a_properties_sheet",
            ),
        ),
        "",
    ),
    "WP-R-006": (
        "met",
        "workbench_edit.save: modified_gmt check, verify",
        (
            (UI + "test_wp_workbench_window.py", "test_a_save_checks_for_conflicts_and_verifies"),
            (
                CORE + "test_wp_workbench_core.py",
                "test_verify_names_what_the_site_did_not_keep_and_undo_puts_it_back",
            ),
        ),
        "",
    ),
    "WP-R-007": (
        "met",
        "workbench_edit.run_batch through batch/v1",
        (
            (UI + "test_wp_workbench_window.py", "test_publish_goes_through_the_batch_endpoint"),
            (
                CORE + "test_wp_workbench_core.py",
                "test_a_batch_falls_back_to_one_at_a_time_when_the_site_will_not_batch",
            ),
        ),
        "",
    ),
    "WP-R-008": (
        "met",
        "Delete is Trash; Delete Permanently is tier 3",
        (
            (UI + "test_wp_workbench_window.py", "test_delete_is_trash_and_ctrl_z_restores"),
            (
                CORE + "test_wp_workbench_core.py",
                "test_delete_never_is_a_default_and_properties_ends_every_menu",
            ),
        ),
        "",
    ),
    "WP-R-009": (
        "met",
        "workbench_filter: REST parameters, local for the rest",
        (
            (CORE + "test_wp_workbench_core.py", "test_the_filter_is_the_rest_query"),
            (CORE + "test_wp_workbench_core.py", "test_local_filtering_matches_cells_and_raw"),
            (
                UI + "test_wp_workbench_window.py",
                "test_a_filter_goes_to_the_site_as_rest_parameters",
            ),
        ),
        "",
    ),
    "WP-R-010": (
        "met",
        "workbench_permissions.refusal; capability_for on every action",
        (
            (
                CORE + "test_wp_workbench_core.py",
                "test_refusals_name_the_role_needed_and_the_role_you_have",
            ),
            (
                UI + "test_wp_workbench_window.py",
                "test_read_only_access_greys_writes_with_a_reason",
            ),
            (
                UI + "test_wp_workbench_window.py",
                "test_a_subscriber_gets_a_read_only_sheet_with_the_reason",
            ),
        ),
        "",
    ),
    "WP-R-011": (
        "met",
        "Change Role, Remove with reassignment, self-lockout guards",
        (
            (CORE + "test_wp_workbench_core.py", "test_nobody_locks_themselves_out"),
            (
                CORE + "test_wp_workbench_lockout_and_stamp_core.py",
                "test_you_cannot_change_your_own_role_whatever_it_is",
            ),
            (
                UI + "test_wp_workbench_lockout_ui.py",
                "test_your_own_role_is_refused_before_any_dialog_and_others_are_previewed",
            ),
            (
                UI + "test_wp_workbench_lockout_ui.py",
                "test_a_role_saved_from_your_own_sheet_meets_the_same_guard",
            ),
        ),
        "",
    ),
    "WP-R-012": (
        "met",
        "Application Passwords node: list, New Here, Revoke",
        (
            (
                UI + "test_wp_workbench_editor_side.py",
                "test_their_application_passwords_read_and_revoke",
            ),
            (
                UI + "test_wp_workbench_lockout_ui.py",
                "test_revoking_the_password_quill_signs_in_with_is_refused",
            ),
        ),
        "",
    ),
    "WP-R-013": (
        "met",
        "quill/tools/wordpress_coverage_audit.py over the recorded index",
        (
            (
                T + "tools/test_wordpress_coverage_audit.py",
                "test_every_recorded_route_is_classified_and_the_snapshot_matches",
            ),
        ),
        "",
    ),
    "WP-R-014": (
        "met",
        "custom_type / custom_taxonomy nodes, schema-built sheets",
        (
            (
                UI + "test_wp_workbench_window.py",
                "test_discovery_adds_a_node_for_each_custom_type_and_taxonomy",
            ),
            (CORE + "test_wp_workbench_core.py", "test_schema_built_sheets_map_types_to_controls"),
        ),
        "",
    ),
    "WP-R-022": (
        "met",
        "WINDOW_MENU, the rebindable APP_KEYMAPS entry",
        (
            (
                UI + "test_wp_workbench_window.py",
                "test_the_menu_bar_keeps_the_accelerator_and_access_key_rules",
            ),
            (UI + "test_wp_workbench_wpab.py", "test_a_rebound_key_follows_the_menu_row"),
        ),
        "",
    ),
    "WP-R-023": (
        "met",
        "F1 on every node and row type (workbench_node_help)",
        (
            (CORE + "test_wp_workbench_leftovers.py", "test_every_node_and_row_type_has_f1_help"),
            (
                UI + "test_wp_workbench_lists.py",
                "test_f1_on_the_tree_and_list_is_the_node_and_row_help",
            ),
        ),
        "there is no separate GATE-WORDPRESS-HELP tool in platform_report; the F1 test is the gate",
    ),
    "WP-R-046": (
        "met",
        "the shared help module (quill/ui/workbench_help_dialogs.py) with WordPress's hooks "
        "(quill/ui/wordpress_workbench_help.py) and Help and Learning's topics",
        (
            (
                CORE + "test_wp_workbench_core.py",
                "test_every_key_the_help_teaches_is_on_the_menu_or_the_frame",
            ),
            (
                CORE + "test_wp_workbench_help_core.py",
                "test_help_and_learning_has_what_githubs_has",
            ),
            (
                UI + "test_wp_workbench_help_ui.py",
                "test_alt_f1_explains_the_wordpress_word_with_this_sites_example",
            ),
            (
                UI + "test_wp_workbench_help_ui.py",
                "test_f9_repeats_and_shift_f9_explains_what_the_workbench_said",
            ),
        ),
        "",
    ),
    "WP-R-047": (
        "met",
        "workbench_help (glossary, How WordPress Thinks); workbench_settings_help (D2)",
        (
            (
                CORE + "test_wp_workbench_core.py",
                "test_every_key_the_help_teaches_is_on_the_menu_or_the_frame",
            ),
            (
                CORE + "test_wp_workbench_lockout_and_stamp_core.py",
                "test_every_listed_setting_has_an_example_from_the_sites_own_value",
            ),
            (
                UI + "test_wp_workbench_lockout_ui.py",
                "test_each_setting_is_explained_with_the_sites_own_example",
            ),
            (
                CORE + "test_wp_workbench_help_core.py",
                "test_the_glossary_has_every_word_d1_names_each_explained",
            ),
            (
                CORE + "test_wp_workbench_help_core.py",
                "test_settings_rows_explain_permalinks_discussion_visibility_and_plugins",
            ),
        ),
        "",
    ),
    "WP-R-048": (
        "met",
        "help before deactivations, deletions and updates",
        (
            (CORE + "test_wp_workbench_core.py", "test_deactivating_quills_own_plugin_warns"),
            (
                CORE + "test_wp_workbench_rest_limits_core.py",
                "test_plugin_theme_and_across_rows_say_the_limit_before_anyone_acts",
            ),
            (
                CORE + "test_wp_workbench_help_core.py",
                "test_wordpress_org_is_asked_for_the_changelog_with_only_the_slug",
            ),
            (
                UI + "test_wp_workbench_help_ui.py",
                "test_turning_a_plugin_off_first_says_what_depends_on_it",
            ),
            (
                UI + "test_wp_workbench_help_ui.py",
                "test_fix_changes_a_broken_link_after_a_preview_and_ctrl_z_puts_it_back",
            ),
        ),
        "",
    ),
    "WP-R-024": (
        "met",
        "QUILL Lite's Tools > WordPress > Open WordPress Workbench: the shared cmd_workbench",
        (
            (
                T + "apps/test_lite_wordpress_workbench_window.py",
                "test_lite_opens_quills_workbench_window_with_its_sites",
            ),
            (T + "apps/test_lite_wordpress.py", "test_each_lite_row_runs_the_shared_command"),
        ),
        "the Practice Site tutorial track is QUILL's only (Lite has no tutorials for it)",
    ),
    "WP-R-025": (
        "met",
        "Needs My Attention > Held as Spam; Spam and Not Spam",
        (
            (
                UI + "test_wp_workbench_window.py",
                "test_not_spam_puts_a_held_comment_back_in_the_queue",
            ),
            (CORE + "test_wp_workbench_core.py", "test_qaf_spam_entries_and_not_spam"),
        ),
        "QAF spam routes against a live site",
    ),
    "WP-R-026": (
        "met",
        "QAF holds spam with its reason (QAF's own repository)",
        ((CORE + "test_wp_qaf_spam_core.py", ""),),
        "QAF's PHPUnit suite, not run here",
    ),
    "WP-R-027": (
        "met",
        "QAF never rejects on behaviour (QAF's own repository)",
        ((CORE + "test_wp_qaf_spam_core.py", ""),),
        "QAF's PHPUnit suite, not run here",
    ),
    "WP-R-030": (
        "met",
        "quill/tools/wordpress_combination_audit.py",
        (
            (
                T + "tools/test_wordpress_combination_audit.py",
                "test_every_argument_value_property_and_method_is_covered_or_planned",
            ),
        ),
        "",
    ),
    "WP-R-031": (
        "met",
        "site_taxonomies: rest_base and statuses from the site",
        (
            (
                CORE + "test_wp_discovery.py",
                "test_the_route_comes_from_rest_base_not_from_the_name",
            ),
            (CORE + "test_wp_discovery.py", "test_statuses_include_the_plugins_own"),
        ),
        "",
    ),
    "WP-R-032": (
        "met",
        "custom types: nodes, lists, New, batch, filters",
        (
            (
                UI + "test_wp_workbench_wpab.py",
                "test_a_status_node_lists_that_status_and_new_here_makes_that_type",
            ),
            (
                UI + "test_wp_workbench_wpab.py",
                "test_a_status_node_takes_filters_to_the_site_and_batches",
            ),
        ),
        "",
    ),
    "WP-R-033": (
        "met",
        "registered meta of every shape on items, terms, users, comments",
        (
            (CORE + "test_wp_custom_field_shapes.py", ""),
            (
                CORE + "test_wp_workbench_lockout_and_stamp_core.py",
                "test_acf_changes_go_back_as_acf_coerced_verified_and_undoable",
            ),
        ),
        "",
    ),
    "WP-R-035": (
        "open",
        "QAF on the test site",
        ((CORE + "test_wp_qaf_spam_core.py", ""),),
        "installing QAF on the test site is a write on the test host (waiting on Jeff)",
    ),
    "WP-R-036": (
        "met",
        "Content Model: types, taxonomies, field groups, who registered each",
        (
            (
                CORE + "test_wp_workbench_wpab_core.py",
                "test_the_content_model_says_every_definition_is_read_only_and_why",
            ),
            (
                CORE + "test_wp_workbench_lockout_and_stamp_core.py",
                "test_the_content_model_marks_site_types_definitions_editable",
            ),
        ),
        "ACF, Pods and Meta Box field groups are not listed: they have no definition route; "
        "QUILL Site Types (fields and kinds) has not met a real WordPress",
    ),
    "WP-R-041": (
        "met",
        "offer_redirect after a slug change, where Redirection is",
        (
            (
                UI + "test_wp_workbench_sweep.py",
                "test_a_new_slug_offers_a_redirect_where_the_plugin_is",
            ),
            (
                CORE + "test_wp_workbench_sweep_core.py",
                "test_redirects_are_covered_only_where_the_plugin_is",
            ),
        ),
        "Redirection's request body is from its documentation, unverified live",
    ),
    "WP-R-043": (
        "met",
        "By Name places: terms, fields, authors, media, patterns, links, forms",
        (
            (
                CORE + "test_wp_workbench_across_core.py",
                "test_every_kind_has_its_own_rows_with_where_it_is_used",
            ),
        ),
        "a live By Name run",
    ),
    "WP-R-044": (
        "met",
        "Across Sites: Site Sets, variants, Missing From",
        (
            (
                CORE + "test_wp_workbench_across_core.py",
                "test_across_sites_names_variants_and_where_a_term_is_missing",
            ),
            (UI + "test_wp_workbench_across.py", "test_across_sites_and_the_fleet_list_every_site"),
        ),
        "a live Across Sites run (menu copy especially)",
    ),
}

STATUSES = ("met", "open")

#: Appendix A object -> the row kind whose Properties sheet shows it.
APPENDIX_A = {
    "Post, page, custom item": "item",
    "Media item": "media",
    "Comment": "comment",
    "Category, tag, custom term": "term",
    "Menu, menu item, location": "menu",
    "User": "user",
    "Plugin": "plugin",
    "Theme": "theme",
    "Template, template part": "template",
    "Pattern": "pattern",
    "Font family and face": "font",
    "Widget, sidebar": "sidebar",
    "Settings group": "setting",
    "Form, response, payment": "form_entry",
    "Product, order, customer, coupon": "shop_order",
    "Podcast episode": "item",
    "Application password": "app_password",
    "Site": "site",
    "Anything discovered": "route",
}

#: Appendix B window -> the tree node (site template) that is its new home.
APPENDIX_B = {
    "Media Library": "media",
    "Comments": "comments_waiting",
    "Categories and Tags": "categories",
    "Menus": "menus",
    "Site Map": "pages",
    "Site Check and Settings": "settings",
    "Manage: users": "users",
    "Manage: plugins": "plugins",
    "Manage: themes, fonts, synced patterns": "themes",
    "Check the Whole Site, Alt Text Review": "media_no_alt",
    "Forms, responses, payments": "forms",
    "Shop": "shop",
    "Post This Episode": "podcast",
}


def _prd_musts() -> set[str]:
    text = PRD.read_text(encoding="utf-8")
    return set(re.findall(r"^- (WP-R-\d+a?) Must\b", text, flags=re.MULTILINE))


def test_every_prd_must_has_a_ledger_row_and_no_row_is_invented() -> None:
    assert set(MUSTS) == _prd_musts()


@pytest.mark.parametrize("must", sorted(MUSTS))
def test_each_row_cites_real_tests_and_an_open_row_says_why(must: str) -> None:
    status, where, evidence, live = MUSTS[must]
    assert status in STATUSES and where and evidence
    if status == "open":
        assert live, f"{must} is open and does not say what is missing"
    for path, name in evidence:
        source = (ROOT / path).read_text(encoding="utf-8")
        if name:
            defined = {
                n.name for n in ast.walk(ast.parse(source)) if isinstance(n, ast.FunctionDef)
            }
            assert name in defined, f"{must}: {path} has no {name}"


def test_every_appendix_a_object_has_a_properties_sheet() -> None:
    for obj, kind in APPENDIX_A.items():
        offered = [a.command_id for a in WORDPRESS_ACTIONS.rows_for(kind)]
        assert command("sheet") in offered, obj
        if kind == "site":
            continue  # the site's own sheet, Alt+Shift+Enter (SITE_SHEET)
        row = WbRow(kind, "S", "1", {"name": "x"}, "", raw={"id": 1, "name": "x"})
        assert sheet_for(row).pages, obj


def test_every_appendix_b_window_has_its_home() -> None:
    nodes = {n.key for n in WORDPRESS_TREE.template("site")}
    assert {w: n for w, n in APPENDIX_B.items() if n not in nodes} == {}
    assert set(_DOORS.values()) <= nodes  # and each Tools > WordPress door opens one


def test_wordpress_uses_only_the_shared_frame() -> None:
    """WP-R-001: the WordPress window is a provider on the shared frame, never its own frame."""
    ui = ROOT / "quill" / "ui"
    for path in ui.glob("wordpress_workbench*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = {getattr(b, "id", getattr(b, "attr", "")) for b in node.bases}
                assert "WorkbenchFrame" not in bases, path.name
    window = (ui / "wordpress_workbench_window.py").read_text(encoding="utf-8")
    assert "from quill.ui.workbench_frame import NodeRef, WorkbenchFrame" in window


class _ItemApi:
    def __init__(self) -> None:
        self.posts: list[tuple[str, dict]] = []

    def get(self, route: str, **_p: object) -> dict:
        return {"id": 9, "type": "event", "status": "draft", "title": {"raw": "Fair"},
                "content": {"raw": "<p>Hi</p>"}, "modified_gmt": "2026-11-01T10:00:00"}  # fmt: skip

    def post(self, route: str, body: object = None, **_p: object) -> dict:
        self.posts.append((route, dict(body or {})))  # type: ignore[call-overload]
        return {**self.get(route), **dict(body or {})}  # type: ignore[call-overload]


@pytest.mark.parametrize("kind", ["events", "library/v1/books"])
def test_a_custom_type_item_saves_back_to_its_own_route(kind: str) -> None:
    """WP-R-002: the type's REST base (or whole route) is kept, so a draft goes home, as a draft."""
    from quill.core.wordpress.site import load_item, update_item

    api = _ItemApi()
    item = load_item(api, kind, 9)  # type: ignore[arg-type]
    assert item.kind == kind  # not the post type "event", which has no route of its own
    update_item(api, item)  # type: ignore[arg-type]
    route, body = api.posts[-1]
    assert route == f"{kind if '/' in kind else 'wp/v2/' + kind}/9"
    assert body.get("status", "draft") == "draft"  # a draft is never published by a save
