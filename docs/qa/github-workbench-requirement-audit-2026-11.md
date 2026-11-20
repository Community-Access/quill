# GitHub Workbench requirement audit, November 2026

Checked 2026-11-18 against main, updated the same day for the follow-up pull request, and on 2026-11-19 for GH-R-046 (the You page), GH-R-086, GH-R-157 and GH-R-036, 109, 114, 115, 116 and 118. This is the record of the complete.md 1.3 requirement audit: every id in Part E of [the GitHub Workbench PRD](<../Product Requirement Documents and Specifications/github-workbench-prd.md>), with the code and the test behind each verdict.

## Summary

Of the 100 live requirements, 89 are met and 11 are partly met. GH-R-042 is withdrawn.

| Strength | Met | Partly met | Not met | Total |
| --- | --- | --- | --- | --- |
| Must | 71 | 4 | 0 | 75 |
| Should | 16 | 7 | 0 | 23 |
| May | 2 | 0 | 0 | 2 |

"Sampled" means a few cases of an "every" were checked, not all of them. The tests the audit cites pass; GH-R-002 was checked on Windows and fixed; nothing here was checked with a screen reader.

## Not met

None.

## Partly met

| Id | Strength | Requirement | Evidence and what remains |
| --- | --- | --- | --- |
| GH-R-119 | Must | One source for every help surface (D19), and the measures of D20 | One help catalogue behind F1, Shift+F1, Alt+F1, Search Help and the generated reference (GATE-GITHUB-HELP, `build_help_reference`); D20's measures (timed find-the-answer sessions) not done. |
| GH-R-150 | Must | Across Repositories has a place for every kind in the 22.11 table, a row per name with its variants and... | Labels, Milestones, Topics, Tags, Branches, Rules and Branch Protection, Environments, Secrets, Variables, Webhooks, Deploy Keys and Autolinks by name, grouped category first, and the Fleet (`test_tags_by_name_say_which_commit_each_is_on`, `test_the_by_name_places_are_grouped_category_first`); workflows, templates, Dependabot and CODEOWNERS, people, settings and packages remain decided "not yet" cells in `across_scope_matrix.py`. |
| GH-R-151 | Must | Every operation a kind allows in one repository is offered across a scope, with the preview and a result... | Preview and a result per repository for every by-name kind (`test_environments_are_made_the_same_but_custom_branches_and_foreign_teams_are_not`, `test_a_secret_is_typed_once_sealed_per_repository_and_never_kept`, `test_a_branch_rename_previews_default_protection_and_retargeted_pull_requests`); a write counts only when its single-repository form exists (`test_a_write_across_repositories_is_done_only_when_the_single_repository_one_is`); held back: ruleset Add to Missing, environment Add to Missing, milestone rename and delete, merged-branch delete, release notes together, alert dismissal. |
| GH-R-157 | Must | Repository and item-property checklists announce a Space toggle once, save from Enter, return focus... | `test_space_changes_the_row_once_and_its_text_says_the_new_state`, `test_no_key_handler_can_toggle_a_second_time` (`tests/unit/ui/test_workbench_check_group.py`), `test_repository_features_say_their_state_once_in_the_row`, `test_enter_on_a_checklist_row_saves_and_ok_is_the_default`, `test_focus_comes_back_when_the_save_took_it_away` (`tests/unit/ui/test_github_workbench_properties.py`), `test_the_checklist_checks_adds_once_and_returns_the_checked`; the JAWS, NVDA and VoiceOver checks it names are live checks not yet recorded. |
| GH-R-068 | Should | The access matrix, bulk access changes and access templates | Access matrix as CSV and bulk access changes, now tested (`tests/unit/ui/test_github_workbench_requirement_checks.py::test_the_access_matrix_is_one_sorted_row_per_person_and_repository`, `test_bulk_access_gives_a_team_a_role_on_each_repository_with_an_undo`); access templates not built. |
| GH-R-069 | Should | View As Role, Compare Roles and Why Can't They? | View As Role, Compare Roles, Why Can't They? now tested (`tests/unit/ui/test_github_workbench_requirement_checks.py::test_why_cant_they_names_the_role_needed_and_who_can_change_it` and others), but they read a fixed ability table, not GitHub's real permissions (the open complete.md row). |
| GH-R-088 | Should | The GitHub features listed in 22.1, each as the coverage gate schedules it | Ongoing: the 22.1 features are the 43 open rows of complete.md 1.3. |
| GH-R-105 | Should | The GitHub tutorials of D8 | One GitHub lesson (practice repository) in docs/user guide/tutorials.md; D8 plans eleven, and there is no Help > Tutorials. |
| GH-R-143 | Should | People > My Teams and team review requests in Needs My Attention | People > My Teams (`load_teams`, "teams:mine"); team review requests are a filter attribute but are not in Needs My Attention. |
| GH-R-153 | Should | Promote to Organization wherever GitHub has a shared form | Rulesets, secrets, variables and webhooks (`test_a_secret_promoted_to_the_organization_deletes_copies_only_after`, `test_variables_made_the_same_added_and_promoted`); labels, environments, deploy keys and autolinks have no organization form in GitHub, and the matrix says so. |
| GH-R-154 | Should | The fourth sweep of 22.12, each as the coverage gate schedules it | Ongoing, as the coverage gate schedules it. |

## Every requirement

### E1. The window and its panes

| Id | Strength | Status | Requirement | Evidence |
| --- | --- | --- | --- | --- |
| GH-R-001 | Must | Met | The Workbench is a top-level frame with its own menu bar, status bar and taskbar button, one per app | `workbench_frame.py:133` a top-level wx.Frame with its own menu bar and status bar; `open_github_workbench` reuses the one open window (one per app). `test_every_github_door_opens_the_workbench`, `test_both_editors_reach_the_window_through_the_one_shared_call` |
| GH-R-002 | Must | Met | It never blocks the editor; its dialogs block only it | Checked on Windows with wx 4.3.2 (2026-11-19): ShowModal disabled the editor. Fixed: the Workbench window is marked `_quill_modal_scope`, and `dialog_contract.show_modal_dialog` (through `modal_scope.py`) re-enables every window outside a scoped dialog's own parent chain once its modal loop starts, so a Workbench dialog blocks the Workbench (and a dialog above it) and never the editor. `tests/unit/ui/test_workbench_dialog_scope.py`, including a real modal loop. Native message and file boxes are still Windows' own. |
| GH-R-003 | Must | Met | F6 and Shift+F6 cycle tree, filter, list and details | `test_f6_cycles_the_panes_in_order` (window test); `workbench_frame.py:392` |
| GH-R-004 | Must | Met | It remembers size, panes, last node, expanded nodes, columns and filters per account | Last node, expanded nodes, repositories and people, and now the window's size and tree-pane width, per account (`navigation_state.WorkbenchPlace` size/sash, `workbench_frame_commands` `restore_layout/remember_layout`); `tests/unit/ui/test_github_workbench_requirement_checks.py::test_the_window_opens_at_last_times_size_and_remembers_it_on_close`. Columns and filters are not in PRD 3.1's list. |
| GH-R-005 | Must | Met | Escape clears the filter, then goes Back, and never closes the window | `test_escape_clears_the_filter_then_goes_back`, `test_escape_in_details_returns`... |
| GH-R-006 | Must | Met | Switch to Editor and Open in Editor raise the editor that opened it | `switch_to_editor` (`workbench_frame_actions.py`) raises and focuses the editor, or says it has closed; `tests/unit/ui/test_github_workbench_requirement_checks.py::test_switch_to_editor_raises_and_focuses_the_editor_that_opened_it` |
| GH-R-007 | Must | Met | The status bar is reached with F6, arrowed across, and every cell has Enter and a context menu with Copy... | `workbench_status_bar.py` (Copy, Help for This Cell, Enter); `test_the_status_bar_reads_name_and_value_and_mirrors_them`; `test_github_workbench_status_cell.py` |

### E2. The tree

| Id | Strength | Status | Requirement | Evidence |
| --- | --- | --- | --- | --- |
| GH-R-010 | Must | Met | The tree is a native `wx.TreeCtrl`, at most four levels deep, loading lazily, with counts after names that... | Native wx.TreeCtrl (`workbench_frame.py`), `test_no_node_is_more_than_four_levels_deep`, rows load on selection; counts after node names ("Issues (12)", "30 or more"), written as the node is left so never announced, none on searches (`workbench_frame_groups.py` `counted_label/write_count`; `test_github_workbench_tree_counts.py`). |
| GH-R-011 | Must | Met | Every view in GitHub Items and Explore appears exactly once (the "nothing dropped" test) | `test_nothing_dropped_every_items_and_explore_view_has_exactly_one_home` |
| GH-R-012 | Must | Met | Nodes needing sign-in, permission or an opt-in are shown, explained, and offer the fix | `github_workbench_window.py` `node_help` ("Needs ...") and unavailable() name the fix; `test_nodes_needing_sign_in_or_permission_are_listed_not_hidden` |
| GH-R-013 | Must | Met | Drill-downs move the tree, and Back and Forward walk one history | `workbench_frame.py` history/forward; `test_escape_clears_the_filter_then_goes_back` asserts forward stack |
| GH-R-014 | Should | Met | Group By puts groups in the tree as child nodes | `test_group_by_puts_groups_in_the_tree` |

### E3. Menus and context menus

| Id | Strength | Status | Requirement | Evidence |
| --- | --- | --- | --- | --- |
| GH-R-020 | Must | Met | Every menu row shows its key; no key is claimed twice; greyed rows carry a reason | `test_the_menu_bar_keeps_the_accelerator_and_access_key_rules`, `tests/unit/ui/test_menu_accelerators.py`, greyed reasons: `test_shift_f1_lists_every_action_with_its_key_and_why_greyed`, `test_merge_is_greyed_on_an_issue_with_a_reason` |
| GH-R-021 | Must | Met | Context menus hold only rows for the selected row type, the default first and Properties last, with More... | `test_github_item_actions.py` rules 1,2,3,6 (default first, only rows about the row, More keeps everything, Properties last) |
| GH-R-022 | Must | Met | Codespaces appears only on repositories, branches and pull requests; Rate Limit on no context menu | `test_rule_4_codespaces_only_on`..., `test_rule_5_the_rate_limit_is_on_no_context_menu` |
| GH-R-023 | Must | Met | Menus, context menus, Shift+F1 and sheets are all built from one action table | Menus/context/Shift+F1 from provider.actions (`workbench_frame_help.py:115`); `test_a_command_appears_once_per_row_type` |

### E4. Properties

| Id | Strength | Status | Requirement | Evidence |
| --- | --- | --- | --- | --- |
| GH-R-030 | Must | Met | Alt+Enter, Item > Properties... and the context menu's last row open the Properties sheet of the selected... | `test_every_appendix_c_object_has_a_sheet_that_opens_on_general` (perm gate), `test_alt_enter_opens_the_sheet_for_the_selected_row`, `test_alt_enter_on_the_repository_node`... |
| GH-R-031 | Must | Met | Every fact is a focusable labelled control; read-only facts are read-only text boxes | `workbench_properties_sheet.py:259` `TE_READONLY` for read-only facts, labels on every field; `test_a_sheet_opens_on_general_and_names_fields_once` |
| GH-R-032 | Must | Met | An editable field is editable exactly when the user may change it, and read-only with a reason otherwise | `test_fields_lock_with_a_reason_when_your_role_is_too_low`; sheet shows "Read only: reason" (`sheet.py:199`) |
| GH-R-033 | Must | Met | A multiple selection opens one sheet with Mixed values and three-state check lists, saving only touched fields | `test_several_rows_open_one_sheet_with_three_state_lists`; `properties.py` Mixed; `test_a_plan_sends_only_changed_fields` |
| GH-R-034 | Must | Met | Before saving, someone else's changes are detected and the user chooses per field; after saving, the... | `test_someone_else_s_change_stops_the_save_until_you_choose`, `test_save_verifies_and_reports_only_what_the_re_read_proves` |
| GH-R-035 | Must | Met | Every picker ends with New... that creates and uses the thing | New Label..., New Milestone..., New Project..., New Issue Type... and New Branch... (`github_workbench_create.py`; `test_new_project_creates_one`..., `test_github_workbench_picker_new.py`). Pickers for people and teams have Add..., since a person or team cannot be made from a sheet. |
| GH-R-036 | Should | Met | Alt+Enter on a GitHub reference in a document opens its sheet | Both editors' key handlers ask one shared call first (`github_editor_line.alt_enter_on_reference`, from `main_frame._on_editor_char_hook` and QUILL Lite's `lite_window_typing._on_key_down`): with the caret on `#42`, `owner/name#42`, `@person`, a commit hash or a GitHub issue, pull request, discussion or commit address (`editor_line.references_in`, `sheet_request`), Alt+Enter opens that object's Properties sheet in the Workbench (the `properties:` door, `github_workbench_reference_sheet.py`; a bare `#42` is read first to choose issue or pull request); anywhere else the key goes on as before. Not a keymap chord, so Alt+Enter is taken nowhere else (rules 1 and 7; the reason is in `keymap.py` and `workbench_menu.line_key_bindings`); the same key in both editors, so no parity divergence. Open the GitHub Reference at the Cursor now opens the sheet too. `tests/unit/ui/test_github_editor_line.py::test_alt_enter_opens_the_sheet_only_on_a_reference`, `tests/unit/ui/test_github_reference_sheet.py`, `tests/unit/core/github_workbench/test_editor_line.py::test_addresses_are_references_with_their_kind` |

### E5. Editing

| Id | Strength | Status | Requirement | Evidence |
| --- | --- | --- | --- | --- |
| GH-R-040 | Must | Met | Every field GitHub's API can change has a control on its object's sheet; the coverage gate proves it | GATE-GITHUB-COVER: `tests/unit/core/test_github_api_coverage.py` (every operation accounted, planned may only shrink); field writes: `test_every_phase_7_sheet_opens_on_general_and_has_writes_for_its_editable_fields` |
| GH-R-041 | Must | Met | Removal and replacement are as available as adding, lifting today's add-only batch rule | Three-state removal: `test_a_three_state_delta_becomes_the_item_s_own_additions_and_removals`; GH-R-041 cited in 3 modules |
| GH-R-042 | Withdrawn | n/a | Per-property keys (withdrawn 2026-11-09) | Alt+Enter opens the sheet instead. |
| GH-R-043 | Must | Met | Batches preview, run paced for the rate limit, and report a result per item with retry | `batch.py` (preview, 1 s pace, result per item), `github_workbench_results.py` Retry Failed (F8); `test_a_batch_previews_skips_what_is_already_so_and_reports_each_item` |
| GH-R-044 | Must | Met | Undo GitHub Change reverses any reversible change, and an irreversible one says so before it happens | `test_undo_is_the_inverse_and_says_what_cannot_be_undone`, `test_ctrl_z_in_the_list_undoes_the_last_github_change` |
| GH-R-045 | Must | Met | Projects (version 2): every field type, items and status updates are readable and editable; views and workflows readable and read only | `sheets_projects.py`: every field type incl. iteration, items, status updates editable; views and workflows read only because GitHub has no API to change them, which the PRD (16.6 and GH-R-045) now says. |
| GH-R-046 | Must | Met | Every relationship (star, watch level, follow, subscribe, react, block, sponsor, pin) on a You page and in... | A You page right after General on every sheet with a relationship (`sheets_you.py` `YOU_PAGES`): repository (Starred, Watch level), gist (Starred), person (Following, Blocked), organization (Following, public membership), issue (Subscribed, reactions, Pinned), pull request and discussion (Subscribed, reactions; Upvoted), release (reactions), notification (Subscribed). Writes are the menu rows' own calls (Follow Organization and Upvote share `sheet_fields.input_mutation`), saved through the checked Properties path, so Read Only and Safe Mode lock them. Sponsoring, pins to your profile, custom watching and a pull request's or discussion's pin read only, each saying why. Batch: the multi-row sheet shows Mixed and changes each row. `tests/unit/core/workbench/test_github_you_page.py` (every kind, a write per kind, batch, read-only reasons, levels). Subscribe and Block have no menu row of their own; the You page is their row. |

### E6. Filtering

| Id | Strength | Status | Requirement | Evidence |
| --- | --- | --- | --- | --- |
| GH-R-050 | Must | Met | One query, written by the filter box, the Filter Builder, the Filter menu and Show Only or Hide on cells,... | `filter_menu.py` (one query for box, builder, menu, Show Only/Hide); `test_quick_filters_toggle_in_the_one_query`, `test_a_query_round_trips_through_the_builder` |
| GH-R-051 | Must | Met | Every attribute GitHub search supports is sent to GitHub; every other attribute filters locally with an... | (sampled) `test_words_filter_here_and_qualifiers_ask_github`, `test_has_conflicts_filters_locally_and_says_so`; Load More/Load All in `github_workbench_explore.py`. "Every attribute" not checked one by one. |
| GH-R-052 | Must | Met | Every list attribute has "has none"; every person field has "Me" | `filter_builder.py`: has none/has any on every person and list attribute, Me as @me; `tests/unit/ui/test_github_workbench_requirement_checks.py::test_every_person_and_list_attribute_offers_has_none_and_has_any`, `test_me_is_sent_as_at_me_and_read_back_as_me` |
| GH-R-053 | Must | Met | Filters can be saved as searches and pinned as nodes | Save Search (`github_workbench_actions.py`), Saved Searches node in the tree (`workbench_tree.py`), and Pin as Node / Unpin Node giving a saved search a node of its own under Saved Searches whose list is the search's results (`workbench_tree_more.PINNED_SEARCH`; `test_github_workbench_pinned_search.py`). |
| GH-R-054 | Should | Met | Or groups where GitHub search allows them | `filter_builder.render_query` brackets groups and joins them with OR; `tests/unit/ui/test_github_workbench_requirement_checks.py::test_or_groups_are_bracketed_and_joined_by_or` |

### E7. Permissions

| Id | Strength | Status | Requirement | Evidence |
| --- | --- | --- | --- | --- |
| GH-R-060 | Must | Met | Account > GitHub Permissions lists every scope the Workbench can use, what each unlocks, and whether you... | `test_github_permissions_lists_every_scope_and_adds_the_missing_in_one_step`, `test_every_scope_the_prd_names_is_in_the_catalogue`, `test_the_three_ways_to_add_missing_scopes` |
| GH-R-061 | Must | Met | The viewer fields of Appendix F.1 are fetched with each object and drive greying with reasons | `test_a_load_reads_the_object_and_its_viewer_fields`, `test_an_optional_viewer_read_that_fails_leaves_the_rest` |
| GH-R-062 | Must | Met | Every write command and editable field declares its requirement and tier; GATE-GITHUB-PERM fails on one... | GATE-GITHUB-PERM: `test_every_write_command_declares_a_requirement_and_a_tier`, `test_every_editable_field_has_a_write_with_requirement_and_tier` |
| GH-R-063 | Must | Met | Every object with an access list has an Access page with Add, Change Role, Remove and pending invitations | Repository and organization Access pages list People, Teams and Pending invitations (`sheets_repo.py`, `sheets_orgs.py`) with Add..., Change... and Remove; on Pending invitations, Remove cancels the invitation and Change... changes the role a repository invitation offers (`access_invitations.py`, `github_workbench_invitations.py`); `tests/unit/core/github_workbench/test_access_invitations.py`. Team invitations are shown on the organization's page, where GitHub cancels them. |
| GH-R-064 | Must | Met | Rulesets and branch protection expose every rule and setting GitHub offers, with a plain-words Summary page | `rulesets.py` every rule and a Summary page; `test_a_ruleset_reads_as_one_plain_sentence`, `test_a_ruleset_sheet_edits_rules_and_sends_the_whole_ruleset_back`, `test_classic_protection_reads_through_the_same_summary` |
| GH-R-065 | Must | Met | Tier 2 changes preview in words; tier 3 adds typed confirmation; self-lockout is refused | Tier 2 preview, TypedConfirmDialog for tier 3 (`github_workbench_tier2.py:337`), `test_removing_your_own_admin_role_is_refused`, `test_destructive_writes_are_tier_3`... |
| GH-R-066 | Must | Met | Read Only, Organize and Full per account; Safe Mode makes every account Read Only | `permissions.py:145`; `test_account_levels_and_safe_mode`, `test_safe_mode_and_read_only_lock_every_field_of_every_sheet`, `test_the_account_level_is_kept_and_read_only_locks_every_field` |
| GH-R-067 | Must | Met | Change History records every write, with before and after, and never a secret | `change_log.py` (atomic, redacted, before/after); `test_change_history_is_atomic_kept_ninety_days_and_never_holds_a_token`, `test_change_history_lists_changes_and_undoes_one`. "Every write" sampled, not proven. |
| GH-R-068 | Should | Partly | The access matrix, bulk access changes and access templates | Access matrix as CSV and bulk access changes, now tested (`tests/unit/ui/test_github_workbench_requirement_checks.py::test_the_access_matrix_is_one_sorted_row_per_person_and_repository`, `test_bulk_access_gives_a_team_a_role_on_each_repository_with_an_undo`); access templates not built. |
| GH-R-069 | Should | Partly | View As Role, Compare Roles and Why Can't They? | View As Role, Compare Roles, Why Can't They? now tested (`tests/unit/ui/test_github_workbench_requirement_checks.py::test_why_cant_they_names_the_role_needed_and_who_can_change_it` and others), but they read a fixed ability table, not GitHub's real permissions (the open complete.md row). |

### E8. Templates

| Id | Strength | Status | Requirement | Evidence |
| --- | --- | --- | --- | --- |
| GH-R-070 | Must | Met | Issue forms and discussion forms are filled natively, with bodies identical to GitHub's | `test_complete_answers_give_githubs_body` (issue form dialog), `test_new_discussion_fills_the_categorys_form`, `test_forms_open_with_the_repositorys_labels_and_assignees` |
| GH-R-071 | Must | Met | Every template kind in 21.2 can be listed, created, edited field by field, checked, previewed and saved | `test_github_workbench_templates.py`: new, builder adds/moves/removes/checks, sheets build files, broken form opens as source; every 21.2 kind in `template_data.py` |
| GH-R-072 | Should | Met | Forms can be written as BFL and converted to and from GitHub's schema through `interop_github.py` | `core/forms/interop_github.py`; `test_forms_interop_github.py` (round trips, refusals) |
| GH-R-073 | Should | Met | Copy to Repositories for templates and community files | `test_copy_previews_then_reports_each_repository`, `test_copy_a_whole_set_from_the_chooser` |

### E9. Beyond parity

| Id | Strength | Status | Requirement | Evidence |
| --- | --- | --- | --- | --- |
| GH-R-080 | Must | Met | The API Console reaches any REST or GraphQL operation, with scope shown, tiers applied and Change History kept | `github_api_console.py`: scope and tier on the What it does line, writes need Full access and the method typed, written to Change History (`_record`); `test_a_console_write_needs_full_access_and_the_method_typed`, `test_the_console_reads_explains_and_shows_a_tree` |
| GH-R-081 | Should | Met | Read as Document for threads, with export | `test_read_as_document_opens_the_thread_in_the_editor`, `test_read_as_document_saves_html_from_a_discussion_row`, `test_a_pull_request_reads_as_one_document_in_time_order` |
| GH-R-082 | Should | Met | Posts are checked for accessibility before sending, offering and never blocking | `comment_compose.accessibility_findings`, offered in `github_comment_composer.py`, never blocks; `test_comment_compose.py` |
| GH-R-083 | Should | Met | Watches with one-sentence results and sounds through the shared feedback channels | Watches with one-sentence results (`test_a_first_check_learns_then_only_new_things_are_said`, `test_add_edit_pause_check_and_remove_a_watch`), and their results now play through the shared feedback channels like every Workbench result (`outcome_feedback.py`; `test_outcome_feedback.py`). |
| GH-R-084 | Should | Met | The editor commands of 22.3 | `editor_line.py` / `github_editor_line.py` in both editors; `test_editor_line.py`. Alt+Enter on a reference (C9) is GH-R-036. |
| GH-R-085 | Should | Met | Export of any list; import of issues from CSV | `test_github_workbench_export.py` (any list, as shown), `test_issue_import.py` and `test_github_workbench_import.py` (CSV and Excel) |
| GH-R-086 | May | Met | Plain-language batches through the Command Key work | Tools > Plain-Language Batch... (Ctrl+Shift+S): a fixed grammar without AI (`quill/core/github/plain_batch.py`), the age shared with WordPress (`quill/core/workbench/plain_age.py`), the targets resolved by GitHub's search, an editable checklist, then the several-items batch; `tests/unit/core/github_workbench/test_github_plain_batch.py`, `tests/unit/ui/test_github_workbench_plain_batch.py`. Command Key itself runs in the editor, not the Workbench window, so the sentence is typed in the Workbench, as WordPress's is. |
| GH-R-087 | Should | Met | Dry Run and the practice repository | `dry_run.py` (REST, GraphQL, PyGithub stop before the network), `test_dry_run.py`, `test_github_workbench_dry_run.py`; practice repository `test_practice_repository.py`, `test_github_workbench_practice.py` |
| GH-R-088 | Should | Partly | The GitHub features listed in 22.1, each as the coverage gate schedules it | Ongoing: the 22.1 features are the 43 open rows of complete.md 1.3. |

### E10. Keyboard

| Id | Strength | Status | Requirement | Evidence |
| --- | --- | --- | --- | --- |
| GH-R-090 | Must | Met | Every key in Part C passes the checks in C1 before adoption and lives in the Workbench's `APP_KEYMAPS` entry | `test_every_menu_key_is_the_app_keymap_entry_and_wx_can_bind_it`, `test_every_command_id_is_in_quills_keymap_and_has_no_chord`. The C1 checks themselves (screen reader and AltGr collisions) are only partly automated. |
| GH-R-091 | Must | Met | The families of Part C hold: Ctrl+number goes, Alt+number says, F-keys keep Windows meanings, and... | `test_ctrl_numbers_go_to_places_and_ctrl_shift_numbers_to_repository_parts`, `test_alt_readouts_say_and_move_nothing`, `test_a_go_key_selects_its_node` |
| GH-R-092 | Must | Met | Typing always moves through the tree and lists; no letter is ever a command | None of the Workbench keys is a bare or shifted letter or digit; `tests/unit/ui/test_github_workbench_requirement_checks.py::test_no_workbench_key_is_a_letter_or_digit_on_its_own` |
| GH-R-093 | Must | Met | Every key is rebindable, and the rebinding follows into menus, the reference, Shift+F1 and the Key Describer | `bound_keys` puts the person's bindings over the defaults; the menus, Shift+F1, Alt+Shift+F1 and the Workbench's Key Describer (Help, Ctrl+Alt+K) all say the bound key (`test_a_rebound_key_is_the_one_the_menu_shows`, `test_github_workbench_key_describer.py`); the published keyboard reference lists the defaults by design. |

### E11. Help

| Id | Strength | Status | Requirement | Evidence |
| --- | --- | --- | --- | --- |
| GH-R-100 | Must | Met | F1 answers on every node, row, sheet page, field, menu row and dialog, in layers | GATE-GITHUB-HELP (`tests/unit/tools/test_github_help_audit.py`: inventory matches, nothing missing, catalogue has no gaps); `test_f1_on_the_tree_and_list_follows_the_node` |
| GH-R-101 | Must | Met | Shift+F1 What Can I Do Here? for every selection | `test_shift_f1_lists_every_action_with_its_key_and_why_greyed` |
| GH-R-102 | Must | Met | Alt+F1 glossary, Ctrl+F1 guide chapter, Ctrl+Shift+F1 Search Help | `test_alt_f1_explains_the_word_for_the_row`, `test_a_chapter_topic_opens_the_guide`, `test_search_help_finds_places_commands_words_and_tasks` |
| GH-R-103 | Must | Met | Empty states, greyed rows, previews and errors carry help | (sampled) `test_an_empty_list_says_why`, `test_placeholders_explain_themselves_and_are_greyed`, greyed rows with reasons (020); every coded error having help not checked |
| GH-R-104 | Must | Met | GATE-GITHUB-HELP at zero and the help tests of D10 green | `tests/unit/tools/test_github_help_audit.py` passes (inventory matches, nothing missing, catalogue has no gaps), with the window help tests |
| GH-R-105 | Should | Partly | The GitHub tutorials of D8 | One GitHub lesson (practice repository) in docs/user guide/tutorials.md; D8 plans eleven, and there is no Help > Tutorials. |
| GH-R-106 | Must | Met | Help and Learning in the tree, with every node of D11 | Help and Learning has Start Here, Do Something, The Guide, Words, Keys, Tutorials (the GitHub lessons with progress; open in the Tutorials window or walk here), What Changed, Tips (QUILLBert's, keys checked against the bindings) and Ask a Person (`workbench_tree.py`; `workbench_learning.py`; `test_github_workbench_learning.py`). |
| GH-R-107 | Must | Met | Take Me There and Walk Me Through It on every help topic and task; Do It where the answer is one command | Take Me There, Walk Me Through It (`quill/core/workbench/walk.py`; the shared frame's `start_walk`, F1 repeats, Shift+F1 lists, Escape stops) and Do It where the task is one command (`workbench_help.DO_IT`, greyed otherwise) on every Do Something task (`test_github_workbench_walk.py`). |
| GH-R-108 | Must | Met | Shift+F9 Explain That for every result, and Why? on every automatic behaviour | Shift+F9 Explain That (`workbench_window_menu.py`, frame `explain_result`), and Why? on what happens on its own: a watch, a notification, a filter applied locally (`quill/core/github/why.py`, `github_workbench_why.py`), listed first by Shift+F1; greyed commands and read-only fields already say why (`test_github_workbench_why.py`). |
| GH-R-109 | Should | Met | Examples from the person's own data and situation | F1 in the Workbench ends with an example built from what the window has loaded: the repository, the selected row and the signed-in account ("On Community-Access/quill, #42 Crash on start is selected: Alt+Enter opens everything about it"); none when it knows too little; nothing is read or sent for it (`help_examples.example_for`, the provider's `help_example` hook in `workbench_frame_help.show_layered_help`). `tests/unit/core/github_workbench/test_help_examples.py` |
| GH-R-115 | Should | Met | Key cards in print and braille, the guide as a book, the spoken tour | Key cards generated from the window's key table: `docs/github/key-card.html` (an accessible print card) and `docs/github/key-card-braille-ready.txt` (ASCII, 40 cells by 25 lines, form feeds) by `python -m quill.tools.build_github_key_card`, drift-gated (`tests/unit/tools/test_github_key_card.py`). The whole guide as one book for each editor, `github-guide-book.md/.epub` and `lite-github-guide-book.md/.epub`, by `python -m quill.tools.build_github_guide_book`, drift-gated (`tests/unit/tools/test_github_guide_book.py`). The spoken tour: Help > Take the Tour (Alt+Shift+T), and once on the first visit, a step per pane through the announcements, F6 on, Escape skips (`workbench_tour.py`, `github_workbench_tour.py`, on the Walk Me Through It engine). D15's Word and DAISY editions and recorded audio of the guide are not made. |
| GH-R-116 | Should | Met | QUILLBert and QUILLBee tips at the right moment, with an option for plain help | A tip is offered in the details pane, unspoken, the third time a slow way is done (a long list without the filter, Properties one row at a time, Load More again and again), once per tip, remembered per person (`workbench_tips.TipMoments`, `offer_tip` in `github_workbench_view.py`); Workbench Options, General: Offer a tip when it would help, and Plain help, without QUILLBert and QUILLBee (Tips and Words drop the names: `workbench_tips.voice`). Words are QUILLBee's. `tests/unit/core/github_workbench/test_workbench_tips.py` |
| GH-R-117 | Must | Met | Ask a Person and Report a Help Problem, never sending a secret | Ask a Person node (mail to support, nothing sent by QUILL); Report a Help Problem on every topic opens a mail with the place and the last thing said, scrubbed of secrets first (`workbench_help.help_report_mailto`, `redact_text_for_bundle`; `test_github_workbench_help_problem.py`). |
| GH-R-118 | May | Met | Ask How through the family's AI, grounded only in the help catalogue | Help > Ask How... (Alt+Shift+A): the help records and menu rows that meet the question (`ask_how.passages` over `ask_how.corpus`) go with an instruction to answer only from them and otherwise to say "The GitHub help does not cover that."; when no help meets it, no request is made. Sent through the opening editor's Choose Your AI (`github_workbench_ask_how.ask_through_editor`: the hosted-AI readiness and capability gates and `AiService.ask`), the same in both editors; the answer is a list with a Do It row per command it names, run only when chosen. Greyed without an AI connection and in Safe Mode. `tests/unit/core/github_workbench/test_ask_how.py` |
| GH-R-119 | Must | Partly | One source for every help surface (D19), and the measures of D20 | One help catalogue behind F1, Shift+F1, Alt+F1, Search Help and the generated reference (GATE-GITHUB-HELP, `build_help_reference`); D20's measures (timed find-the-answer sessions) not done. |

### E12. Speech, braille and sound

| Id | Strength | Status | Requirement | Evidence |
| --- | --- | --- | --- | --- |
| GH-R-110 | Must | Met | The Workbench announces only what the reader cannot see (results, background changes, Watches) and nothing... | GATE-13 (`check_over_announce.py` scans quill/ui, which holds every Workbench module); the frame speaks results only (`workbench_frame_commands._say`) |
| GH-R-111 | Must | Met | Every announcement is also brailled | The Workbench speaks only through the announce callback the editor passes (its announcement service, which brailles); GATE-BRAILLE in `platform_report` |
| GH-R-112 | Must | Met | One sentence per outcome, naming what changed | (sampled) one-sentence results across the window tests, e.g. `test_saving_sends_only_the_change_verifies_it_and_says_one_sentence`, `test_comment_posts_through_items_and_says_one_result` |
| GH-R-113 | Must | Met | Sounds go through the shared action-feedback channels; a failure or a count is always spoken | Results go through `action_feedback` (`quill/core/github/outcome_feedback.py` plan, `quill/ui/github_workbench_feedback.py`): task-complete tone for a change that landed, error tone for a failure, a failure or a count always spoken, a bare acknowledgement by the setting (`test_outcome_feedback.py`). |
| GH-R-114 | Should | Met | A braille-shaped row option | Workbench Options, Lists, Short rows for braille (`braille_rows`): each list is one column whose text is the row shaped for a braille display, number and title first, no column names, abbreviations (cl, PR, 3c, 9 Nov), nothing cut off; Columns... still chooses what the line holds (`core/workbench/braille_rows.py`, `github_workbench_view.shaped_columns/shaped_cells`). `tests/unit/core/workbench/test_github_braille_rows.py` |

### E13. Settings

| Id | Strength | Status | Requirement | Evidence |
| --- | --- | --- | --- | --- |
| GH-R-120 | Must | Met | Every GitHub preference lives in Workbench Options, stored in `github_workbench.json` through... | `workbench_prefs.py` to `github_workbench.json`, shared; `test_the_schema_names_every_field_and_every_choice`, `test_the_options_dialog_saves_to_the_workbench_file`; `settings.py` holds no GitHub fields |
| GH-R-121 | Must | Met | The three poll settings migrate out of the main Settings once, with the vocabulary audit and GATE-SETDOC... | `test_the_three_settings_move_once`, `test_settings_no_longer_hold_them_and_drop_the_old_keys`, `test_the_settings_file_hands_them_over_before_the_load` |
| GH-R-122 | Must | Met | The Workbench is fully usable without opening Workbench Options | (by inspection) every preference has a default (`test_defaults_round_trip_and_bad_values_fall_back`); nothing asks for Options first |

### E14. API use

| Id | Strength | Status | Requirement | Evidence |
| --- | --- | --- | --- | --- |
| GH-R-130 | Must | Met | Only `api.github.com`, `github.com` sign-in pages, `uploads.github.com` for assets and, with consent,... | `network_egress_entries_github.py` names every GitHub endpoint family; githubstatus.com is not on main yet (built today, uncommitted, branch gh/service-status) |
| GH-R-131 | Must | Met | Conditional requests (ETag) for every repeated read (`conditional_requests.py`), and secondary rate limits... | Secondary limits respected in `rest_transport.py` (`secondary_wait_seconds`, `test_a_secondary_limit_stops_every_later_request_with_one_sentence`); every repeated REST read is conditional: Workbench lists through `list_probe.py` (one If-None-Match read of the same window, rows kept on 304) and sheets, pickers and reloads through TokenApi.rest (`test_conditional_reads.py`). GraphQL has no ETag. |
| GH-R-132 | Must | Met | GraphQL where it is the only API (Appendix F) and where one query replaces many REST calls; REST otherwise | (sampled) GraphQL for Projects, Discussions, reviews, team code review; summary queries batch with aliases (`test_summary_query_batches_with_aliases`); REST otherwise |
| GH-R-133 | Must | Met | The vendored API snapshot and `api_coverage.json` drive GATE-GITHUB-COVER | `test_github_api_coverage.py` (1,281 REST operations: 731 covered, 354 out of scope, 196 no API needed; planned ceiling 0) |

### E15. Teams

| Id | Strength | Status | Requirement | Evidence |
| --- | --- | --- | --- | --- |
| GH-R-140 | Must | Met | Teams are created, edited, nested, filled, given repository and project roles, and deleted, from the Team... | New Team and Delete Team (`quick_tables.py`), Team sheet (`sheets_orgs.py`), members and repositories through `access.py`; `api_coverage` marks POST/PATCH/DELETE /orgs/{org}/teams covered. Team creation itself has no test of its own. |
| GH-R-141 | Must | Met | Team code review assignment is readable and editable | `test_team_code_review_is_one_mutation_with_every_setting` |
| GH-R-142 | Should | Met | Batch membership and batch repository roles across teams | Bulk Access Changes (`access.bulk_plan`) for team memberships and team repositories; `tests/unit/ui/test_github_workbench_requirement_checks.py::test_bulk_team_membership_and_its_removal` |
| GH-R-143 | Should | Partly | People > My Teams and team review requests in Needs My Attention | People > My Teams (`load_teams`, "teams:mine"); team review requests are a filter attribute but are not in Needs My Attention. |

### E16. Across repositories

| Id | Strength | Status | Requirement | Evidence |
| --- | --- | --- | --- | --- |
| GH-R-150 | Must | Partly | Across Repositories has a place for every kind in the 22.11 table, a row per name with its variants and... | Labels, Milestones, Topics, Tags, Branches, Rules and Branch Protection, Environments, Secrets, Variables, Webhooks, Deploy Keys and Autolinks by name, grouped category first, and the Fleet (`test_tags_by_name_say_which_commit_each_is_on`, `test_the_by_name_places_are_grouped_category_first`); workflows, templates, Dependabot and CODEOWNERS, people, settings and packages remain decided "not yet" cells in `across_scope_matrix.py`. |
| GH-R-151 | Must | Partly | Every operation a kind allows in one repository is offered across a scope, with the preview and a result... | Preview and a result per repository for every by-name kind (`test_environments_are_made_the_same_but_custom_branches_and_foreign_teams_are_not`, `test_a_secret_is_typed_once_sealed_per_repository_and_never_kept`, `test_a_branch_rename_previews_default_protection_and_retargeted_pull_requests`); a write counts only when its single-repository form exists (`test_a_write_across_repositories_is_done_only_when_the_single_repository_one_is`); held back: ruleset Add to Missing, environment Add to Missing, milestone rename and delete, merged-branch delete, release notes together, alert dismissal. |
| GH-R-152 | Must | Met | Repository Sets, by hand or by filter, usable as the scope of any batch | `test_named_sets_are_made_used_renamed_filtered_and_deleted`, `test_a_filter_set_runs_the_search_and_keeps_what_it_found`, `test_repository_sets_are_per_account_and_validated` |
| GH-R-153 | Should | Partly | Promote to Organization wherever GitHub has a shared form | Rulesets, secrets, variables and webhooks (`test_a_secret_promoted_to_the_organization_deletes_copies_only_after`, `test_variables_made_the_same_added_and_promoted`); labels, environments, deploy keys and autolinks have no organization form in GitHub, and the matrix says so. |
| GH-R-154 | Should | Partly | The fourth sweep of 22.12, each as the coverage gate schedules it | Ongoing, as the coverage gate schedules it. |
| GH-R-155 | Must | Met | Category-first lists cover the eight item kinds in 22.11.1, use an explicit per-account repository set,... | (sampled) `test_category_rows_keep_every_repository_and_enter_then_back_returns`, `test_every_repository_state_has_its_own_sentence`, `test_releases_are_latest_only_until_asked` |
| GH-R-156 | Must | Met | Issue-type and issue-field values in category lists, filters, and Properties retain their stable IDs,... | `test_issue_types_and_fields_keep_their_states_apart`, `test_issue_type_and_fields_are_read_shown_and_filtered` |
| GH-R-157 | Must | Partly | Repository and item-property checklists announce a Space toggle once, save from Enter, return focus... | `test_space_changes_the_row_once_and_its_text_says_the_new_state`, `test_no_key_handler_can_toggle_a_second_time` (`tests/unit/ui/test_workbench_check_group.py`), `test_repository_features_say_their_state_once_in_the_row`, `test_enter_on_a_checklist_row_saves_and_ok_is_the_default`, `test_focus_comes_back_when_the_save_took_it_away` (`tests/unit/ui/test_github_workbench_properties.py`), `test_the_checklist_checks_adds_once_and_returns_the_checked`; the JAWS, NVDA and VoiceOver checks it names are live checks not yet recorded. |
