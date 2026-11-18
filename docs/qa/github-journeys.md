# GitHub journeys GX01 to GX08: what each one is, how it fails, and the evidence

This document closes the first eight rows of the GitHub roadmap's journey
table (`docs/planning/github-roadmap.md`, reproduced in `complete.md` section
GH-F) the way that section asks: each journey as a person walks it, the
failure it must survive, and the evidence that it does. Evidence is the
automated test that walks the same path against recorded GitHub answers, and
the live regression run (`docs/qa/github-live-run.py`, described in
`docs/qa/github-regression-testing.md`) where a journey writes to GitHub.

What no automated test can show is how each step sounds with a screen reader.
The last column of each table says which steps still need a person with JAWS,
NVDA or VoiceOver; those checks are listed together at the end.

Written 2026-11-18, against `main` after pull request #1866.

## GX01: Open a GitHub reference

**The journey.** Someone pastes a link from an email, a chat or a document:
an issue, a pull request, a discussion, a commit, a branch, a file at a line,
a release or a workflow run. QUILL opens the best native view at that exact
place, even when it is not on the first page of its list, and anything it
cannot show natively goes to the browser with a sentence saying why.

**The failure it must survive.** A malformed link, a link with a password or
token in it, a link to an enterprise host, and a link that names an issue but
is really a pull request.

| Step or rule | Evidence |
| --- | --- |
| Every supported shape parses: repository, issue, pull request, discussion, commit, branch, file and line, release, workflow and run | `tests/unit/core/test_github_references.py::test_parses_supported_reference_shapes`; `test_ssh_remote_and_git_suffix_normalize_to_repository` |
| The native view is chosen by kind | `tests/unit/ui/test_github_reference_routing.py::test_reference_kind_selects_the_native_view` |
| An item outside the first page is still found | `test_direct_issue_reference_is_fetched_even_when_outside_first_page`; `test_release_reference_fetches_exact_tag_even_outside_recent_page` |
| An issue link that is a pull request opens the review | `test_issue_url_that_resolves_to_pull_request_opens_review_reader` |
| Exact commit, run and workflow | `test_commit_reference_fetches_the_exact_sha`; `test_workflow_run_reference_fetches_exact_run_id`; `test_workflow_definition_reference_fetches_workflow_file` |
| Unsupported objects fall back to the browser, safely | `test_unsupported_github_object_retains_a_safe_browser_fallback`; `test_discussions_are_native_and_comparisons_use_browser_fallback` |
| Malformed and credential-bearing links never send anything | `test_rejects_malformed_line_anchors`; `test_rejects_malformed_or_credential_bearing_references` |

**Still needs a person:** that the place the view lands on is the place the
screen reader announces first.

## GX02: The personal attention queue

**The journey.** Needs My Attention > Inbox brings together review requests,
mentions, assignments and pull requests with failing checks, across the
repositories the person chose, once each, saying where each came from and
what changed since the last visit. Rows can be snoozed here without touching
GitHub. Notifications sits beside it, with Done, Unsubscribe, Mark All Read
and, since 2026-11-18, inbox rules.

**The failure it must survive.** A partial load must never look like an empty
inbox, and loading must never mark anything read.

| Step or rule | Evidence |
| --- | --- |
| Sources combined and deduplicated, scoped to chosen repositories | `tests/unit/core/test_github_attention_queue.py::test_repository_scope_rejects_invalid_names_and_too_many_repositories`; `tests/unit/core/test_github_notification_triage.py::test_inbox_reads_pages_poll_interval_and_dedupes` |
| Saved filters and preferences per account | `test_queue_preferences_and_saved_filters_are_account_scoped` |
| Local snooze, expiring | `test_snoozes_expire_and_can_be_cleared_locally` |
| Since the last visit | `test_last_visit_only_marks_items_updated_after_the_previous_visit`; `tests/unit/ui/test_github_attention_queue_dialog.py::test_complete_queue_load_advances_last_visit` |
| A partial load keeps the previous visit and says it is partial | `test_partial_queue_load_hides_local_snoozes_and_keeps_previous_visit`; `tests/unit/ui/test_github_workbench_explore_nodes.py::test_a_first_page_that_is_not_everything_says_so` |
| Loading reads nothing as read; GitHub's poll interval is kept | `test_poll_gate_waits_per_query`; `test_inbox_conditional_request_returns_not_modified` |
| Triage uses the documented endpoints and says what really happened | `test_done_unsubscribe_and_read_all_use_the_documented_endpoints`; `test_read_all_accepted_in_background_is_not_claimed_as_done` |
| Inbox rules act only as the person set them, and say what they did | `tests/unit/core/github_workbench/test_inbox_rules.py` |

**Still needs a person:** the reason being read before the title on each row,
at a natural speed.

## GX03: Context-preserving navigation

**The journey.** Moving around the Workbench never loses one's place: Back and
Forward (Alt+Left, Alt+Right) restore the view, its filter, grouping and the
selected row; the Workbench reopens where it was left, per account; a drafted
issue or review comes back after a crash; and every greyed command says what
it needs.

**The failure it must survive.** Returning to a list after the results have
changed, a different account, and a draft written against an older version of
a pull request.

| Step or rule | Evidence |
| --- | --- |
| Back and Forward restore the view and its filter | `test_back_and_forward_restore_repository_view_and_filters`; `test_back_forward_navigation_controls_are_named_and_stateful` |
| The selection comes back after a reload | `test_saved_selection_is_restored_after_results_load` |
| The place is remembered per account | `tests/unit/ui/test_github_workbench_phase3.py::test_the_place_is_remembered_per_account`; `test_restore_navigation_uses_the_same_account_and_repository` |
| Across Repositories: Enter then Back returns to the same row | `test_category_rows_keep_every_repository_and_enter_then_back_returns` |
| Drafts are recovered, and a review draft on an older head asks first | `test_issue_dialog_recovers_edits_and_discards_local_draft`; `test_review_draft_recovers_and_requires_confirmation_after_head_changes` |
| Every greyed command says why | `test_placeholders_explain_themselves_and_are_greyed`; the reasons tables in `quill/ui/github_workbench_*.py`, checked by `tests/unit/ui/test_github_workbench_merge.py::test_verbs_and_reasons_are_registered` and its neighbours |

**Still needs a person:** that returning from the browser or a nested window
puts focus on the same row and the reader says it once.

## GX04: CI diagnosis

**The journey.** A failed run: What Failed gives the failing steps, their
annotations and the end of each log as one text; the jobs window has every
attempt, every job and its full log; Re-run Failed Jobs runs only what failed;
and since 2026-11-18 Follow This Job says each step of a running job as it
happens.

**The failure it must survive.** A truncated or failed log read, an older
result arriving after a newer one, and pressing Re-run twice.

| Step or rule | Evidence |
| --- | --- |
| What Failed opens the digest for the run | `test_what_failed_opens_the_digest_for_the_selected_run`; `test_digest_dialog_shows_text_and_summary` |
| Source and truncation are said | `test_summary_presents_its_github_source_and_truncation_status` |
| Stale results are dropped | `test_workflow_jobs_ignores_older_list_and_log_results`; `test_a_stale_failure_is_dropped_too` |
| Re-run asks, reports what GitHub did, and is not claimed when it fails | `test_rerun_failed_cancel_and_approve_confirm_then_report_what_github_did`; `test_failure_is_reported_not_claimed_as_success` |
| A running job is followed step by step | `tests/unit/ui/test_github_workflow_job_follow.py`; `tests/unit/core/github_workbench/test_job_follow.py` |
| Live: re-run failed jobs, then delete the run | `docs/qa/github_live_verbs.py`, `rerun_failed_and_delete` |
| Re-run Failed Jobs pressed twice before GitHub answers sends one request | `tests/unit/ui/test_github_workbench_items_actions.py::test_a_second_rerun_while_the_first_is_on_its_way_sends_nothing` |

Writing this journey down found that gap: a second press while the first
request was still on its way sent a second re-run. It now says "A re-run of
run #41, CI is already on its way to GitHub." and sends nothing
(`quill/ui/github_workbench_runs.py`, 2026-11-18).

## GX05: Issue intake and triage

**The journey.** New Issue offers the repository's templates and forms, with
required fields named as required; triage closes for a reason (completed, not
planned, a duplicate of a numbered issue), labels, assigns, comments through
the comment window with saved replies, and acts on many at once with a
preview and a result per item.

**The failure it must survive.** A draft must never publish by itself, a
duplicate suggestion must never close anything, and every batch item reports
its own result.

| Step or rule | Evidence |
| --- | --- |
| Templates and forms, required fields named | `test_new_issue_uses_the_selected_repository_template`; `test_required_fields_say_so_in_their_names`; `test_new_issue_submits_edited_template_metadata` |
| A form the builder cannot read is kept, not lost | `test_a_broken_form_opens_as_source_without_losing_it` |
| Close as a duplicate needs the original, and nothing is sent without it | `test_a_duplicate_asks_for_the_original_by_number`; `test_a_duplicate_without_a_number_sends_nothing` |
| Saved replies and the rest of the comment window | `tests/unit/ui/test_github_comment_composer.py` |
| Batch results per item | `tests/unit/ui/test_github_workbench_import.py`; the Across Repositories batch tests |
| Live: close for each reason, labels, assignees, comments | `docs/qa/github_live_verbs.py`, `close_reopen`, `labels`, `assignees`, `comment` |

**Still needs a person:** the issue form read field by field, and the
duplicate question's wording.

## GX06: Projects and dependencies

**The journey.** An issue's sheet shows every project it is in and every field
there, editable; sub-issues are listed in order and can be reordered; blocked
and blocking are on the Relationships page; task-list lines become
sub-issues; and Next Unblocked goes to the next thing that can be started.

**The failure it must survive.** Fields a token cannot edit, and a board read
in a linear order a screen reader can follow.

| Step or rule | Evidence |
| --- | --- |
| Projects on the sheet, added and removed with GraphQL | `test_projects_on_the_sheet_add_and_remove_with_the_graphql_mutations` |
| Dependencies and progress explained on the row | `test_project_item_label_and_details_explain_dependencies_and_progress` |
| Sub-issues reordered, and the order read back | `test_sub_issue_dialog_moves_and_says_where_it_landed`; `test_sub_issue_moves_and_the_order_is_read_back` |
| Task lines become sub-issues | `test_convert_makes_sub_issues_and_links_each_line`; `test_issues_from_lines_makes_sub_issues` |
| Live: sub-issues | `docs/qa/github_live_verbs.py`, `sub_issues`, `task_lists` |

**Still needs a person:** a project board of fifty items read in order.

## GX07: Local repository continuity

**The journey.** From an issue, Start in Local Worktree makes a named branch
in a folder of its own after checking the checkout; a fork's upstream is
known; ahead and behind are said for branches; and since 2026-11-17 a pull
request's conflicts can be resolved in a worktree of their own.

**The failure it must survive.** Dirty files are never overwritten, a checkout
of another repository is refused, and nothing from remote content is run as a
command.

| Step or rule | Evidence |
| --- | --- |
| The worktree hand-off keeps dirty changes where they are | `tests/unit/ui/test_github_issue_worktree_handoff.py::test_issue_handoff_uses_matching_upstream_and_keeps_dirty_changes_in_place` |
| A checkout of another repository is refused | `test_issue_handoff_refuses_a_checkout_for_an_unrelated_repository`; `test_resolve_conflicts_needs_a_checkout_of_that_repository` |
| Conflicts are merged in a new folder, nothing committed | `test_resolve_conflicts_merges_in_a_new_folder_and_walks_each_file`; `tests/unit/core/github_workbench/test_pull_tools.py::test_conflicts_land_in_a_new_worktree_and_are_listed` |
| A branch name that could be a git option is refused | `test_branch_names_that_could_be_options_are_refused` |
| Upstream and ahead and behind | `test_upstream_button_enabled_for_a_fork_and_announces`; `test_the_compare_direction_is_swapped_into_ahead_and_behind` |

**Still needs a person:** the worktree confirmation read in full, and the
Resolve Conflicts walk on a real conflict.

## GX08: Deep accessible review

**The journey.** The review window's outline of files, threads and checks;
Next Unresolved; changes since my last review; files marked viewed; pending
line comments and a review draft; suggestions; and in the diff window,
Changed Lines Only, the line sounds, Hide Whitespace Changes and one commit at
a time.

**The failure it must survive.** Renamed, deleted, binary and very large files,
outdated threads, and a patch GitHub does not send.

| Step or rule | Evidence |
| --- | --- |
| Next Unresolved | `test_next_unresolved_selects_the_next_known_unresolved_thread` |
| Outdated threads are marked | `test_thread_header_carries_place_author_replies_and_outdated`; `test_fetch_review_threads_maps_outdated_from_missing_position` |
| Binary content is refused clearly, and the patch is the fallback | `test_fetch_file_text_rejects_binary_clearly`; `test_selecting_a_file_falls_back_to_patch_on_fetch_error` |
| Viewed files | `tests/unit/core/github_workbench/test_review_viewed.py` |
| Changed lines only, line sounds, whitespace, one commit | `tests/unit/ui/test_github_wave2_review_ui.py` |
| The whole patch names files with no text | `tests/unit/core/github_workbench/test_pull_tools.py::test_patch_is_one_unified_diff_with_every_kind_of_file` |
| A review draft on an older head asks before it is used | `test_review_draft_recovers_and_requires_confirmation_after_head_changes` |

**Still needs a person:** the line sounds at speed, and the outline with a
large pull request.

## The checks that need a screen reader

These are added to `docs/qa/screen-reader-checks-2026-10.md`'s way of working:
one person, one reader, the steps above, and a note of anything said twice,
said late or not said.

1. GX01: the first thing announced after opening a pasted link.
2. GX02: an Inbox row read at normal speed, reason before title.
3. GX03: focus and announcement after returning from the browser.
4. GX04: Follow This Job while a real job runs, and the end of the job.
5. GX05: an issue form, field by field; the duplicate question.
6. GX06: a project board of fifty items in reading order.
7. GX07: the worktree and conflict confirmations read in full.
8. GX08: the line sounds while arrowing quickly; a large outline.
