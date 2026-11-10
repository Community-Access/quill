"""Long lists, New Here, terms, roles, password resets and spam in the WordPress Workbench.

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`
for the W1 to W4 leftovers:

- **Load More and Load All** (View menu): the node reads three hundred more
  rows, or every row, through :class:`~quill.core.wordpress.workbench_listing.Paging`;
  the Items cell says when a list stopped short.
- **Columns** (View > Columns): a check list of the node's own columns and
  the ones its rows can show.
- **Group By** (View > Group By): one child node per value of a column,
  under the node's Group branch (GitHub PRD 17.4); selecting one lists its
  rows. Grouping by nothing removes them.
- **New Here** (Ctrl+N) for posts, pages, custom items, categories, tags,
  custom terms and menus; users and application passwords keep their own.
- **Merge Into and Convert** for terms, each previewed with the number of
  items that move, tier 3.
- **Send Password Reset**, which WordPress keeps out of REST, opens the
  person's wp-admin screen; **Roles** lists each role in plain words.
- **Empty Spam** (tier 3) and **Not Spam, and Allow This Sender**.

Every request runs through ``self.background``; every outcome is one sentence.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from quill.core.wordpress import site_admin as admin
from quill.core.wordpress.workbench_create import (
    ROLES_CANNOT_CHANGE,
    allow_sender_words,
    convert_term,
    creatable,
    create,
    empty_spam,
    merge_preview,
    merge_terms,
    password_reset_pointer,
    role_rows,
    spam_comments,
)
from quill.core.wordpress.workbench_edit import set_comment_status
from quill.core.wordpress.workbench_listing import (
    EXTRA_COLUMNS,
    Paging,
    column_title,
    cut_words,
    extra_cell,
    group_instance,
    group_of,
    groups,
    parse_group,
)
from quill.core.wordpress.workbench_load import MAX_PAGES
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_tree import GROUPED
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg

__all__ = ["WorkbenchListCommands"]

_TAXONOMY_OF_ROUTE = {"categories": "category", "tags": "post_tag"}


class WorkbenchListCommands:
    """Paging, columns, grouping, New Here, terms, people extras and spam."""

    frame: Any
    parent: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    ensure: Callable[[Any], Any]
    profile: Callable[[str], Any]
    show_modal: Callable[[Any, str], int]
    refresh: Callable[[], None]
    site_of: Callable[[Any], str]
    current_site: Callable[[], str]
    selected_rows: Callable[[], list[WbRow]]
    split: Callable[[str], tuple[str, str]]

    def _lists_state(self) -> None:
        if not hasattr(self, "paging"):
            self.paging = Paging(first=MAX_PAGES)
            self.column_choice: dict[str, tuple[str, ...]] = {}
            self.grouping: dict[tuple[str, str], str] = {}
            self.group_values: dict[tuple[str, str], list[tuple[str, int]]] = {}
            self.cut: dict[str, str] = {}

    # -- what the window asks -----------------------------------------------------

    @staticmethod
    def page_key(ref: Any) -> str:
        return f"{ref.template}|{ref.key}|{ref.instance}" if ref is not None else ""

    def pages_for_ref(self, ref: Any) -> int:
        self._lists_state()
        return self.paging.pages(self.page_key(ref))

    def note_loaded(self, ref: Any, count: int) -> None:
        """After a load: remember whether the list stopped at its limit."""
        self._lists_state()
        self.cut[self.page_key(ref)] = cut_words(count, self.pages_for_ref(ref))

    def cut_for(self, ref: Any) -> str:
        self._lists_state()
        return self.cut.get(self.page_key(ref), "")

    def chosen_columns(self, node: Any) -> tuple[str, ...]:
        self._lists_state()
        return self.column_choice.get(node.key, node.columns or ("name",))

    def cell_for(self, row: WbRow, column: str) -> str:
        return extra_cell(row, column)

    def group_children(self, node: Any, ref: Any) -> Sequence[tuple[str, str]]:
        """The Group node's children: one per value of the chosen column."""
        self._lists_state()
        site = self.split(ref.instance)[0]
        parent = node.parent or ""
        column = self.grouping.get((site, parent), "")
        if not column:
            return ()
        values = self.group_values.get((site, parent), [])
        from quill.ui.wordpress_workbench_window import SEP

        return tuple(
            (group_instance(site, SEP, column, value), f"{value} ({count})")
            for value, count in values
        )

    @staticmethod
    def narrow_to_group(kind: str, rows: Sequence[WbRow]) -> list[WbRow]:
        found = parse_group(kind)
        if found is None:
            return list(rows)
        column, value = found
        return [row for row in rows if group_of(row, column) == value]

    # -- View menu ----------------------------------------------------------------

    def _list_ref(self) -> Any:
        frame = self.frame
        if frame is None or frame.current is None or not frame.node(frame.current).loader:
            self.say("Choose a list in the tree first.")
            return None
        return frame.current

    def do_load_more(self, _ref: Any, _row: WbRow | None) -> None:
        ref = self._list_ref()
        if ref is None:
            return
        self._lists_state()
        pages = self.paging.more(self.page_key(ref))
        self.say(f"Reading up to {pages * 100} rows.")
        self.refresh()

    def do_load_all(self, _ref: Any, _row: WbRow | None) -> None:
        ref = self._list_ref()
        if ref is None:
            return
        self._lists_state()
        self.paging.all(self.page_key(ref))
        self.say("Reading every row. A big site takes a while.")
        self.refresh()

    def _available_columns(self, node: Any) -> list[str]:
        own = list(node.columns or ("name",))
        extra = [c for c in EXTRA_COLUMNS.get(node.row_type, ()) if c not in own]
        return own + extra

    def do_columns(self, _ref: Any, _row: WbRow | None) -> None:
        ref = self._list_ref()
        if ref is None:
            return
        frame = self.frame
        node = frame.node(ref)
        names = self._available_columns(node)
        shown = self.chosen_columns(node)
        picked = wdlg.ask_checks(
            self.parent,
            self.show_modal,
            title="Columns",
            prompt="&Columns to show:",
            rows=[column_title(n) for n in names],
            checked=[i for i, n in enumerate(names) if n in shown],
            help_text="Check each column the list shows, in this order. The first is what "
            "your screen reader says first.",
        )
        if picked is None:
            return
        if not picked:
            self.say("A list needs one column at least, so nothing changed.")
            return
        self._lists_state()
        self.column_choice[node.key] = tuple(names[i] for i in picked)
        frame._set_columns(node)
        frame._fill_list()
        self.say(f"{len(picked)} columns.")

    def do_group_by(self, _ref: Any, _row: WbRow | None) -> None:
        ref = self._list_ref()
        if ref is None:
            return
        frame = self.frame
        node = frame.node(ref)
        parent = node.parent if node.key.endswith("_group") else node.key
        if ref.template != "site" or parent not in GROUPED:
            self.say("Group By works on Posts, Pages, Media, Comments and Plugins.")
            return
        from quill.ui.workbench_frame import NodeRef

        site = self.split(ref.instance)[0]
        names = self._available_columns(frame.node(NodeRef("site", parent, site)))
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title="Group By",
            prompt="&Group by:",
            rows=["Nothing (no groups)", *[column_title(n) for n in names]],
            help_text="Each value of the column you choose becomes a node under Group, "
            "with how many rows have it.",
        )
        if index is None:
            return
        self._lists_state()
        if index == 0:
            self.grouping.pop((site, parent), None)
            self.group_values.pop((site, parent), None)
            frame.rebuild_tree()
            self.say("No groups.")
            return
        column = names[index - 1]
        rows = [r for r in frame.rows if isinstance(r, WbRow)]
        self.grouping[(site, parent)] = column
        self.group_values[(site, parent)] = groups(rows, column)
        frame.rebuild_tree()
        count = len(self.group_values[(site, parent)])
        self.say(f"{count} groups under Group, by {column_title(column).lower()}.")

    # -- New Here -----------------------------------------------------------------

    def do_new_here(self, ref: Any, row: WbRow | None) -> None:
        site = self.site_of(ref)
        key = ref.key if ref is not None else ""
        if key in ("users", "app_passwords"):
            super().do_new_here(ref, row)  # type: ignore[misc]
            return
        dynamic = self.split(ref.instance)[1] if ref is not None else ""
        known = {
            **dict(getattr(self, "_types", {}).get(site, [])),
            **dict(getattr(self, "_taxonomies", {}).get(site, [])),
        }
        label = known.get(dynamic, "")
        what = creatable(key, dynamic, dynamic_label=label)
        if what is None or not site:
            self.say(
                "New Here makes posts, pages, custom items, categories, tags, terms, menus, "
                "people and application passwords. Choose one of those nodes first."
            )
            return
        answers: dict[str, str] = {}
        for field_key, prompt, help_text in what.fields:
            text = dlg.ask_text(
                self.parent,
                self.show_modal,
                title=f"New {what.noun.title()}",
                prompt=prompt,
                help_text=help_text,
            )
            if text is None:
                return
            if field_key in ("title", "name") and not text.strip():
                self.say("It needs a name, so nothing was made.")
                return
            answers[field_key] = text.strip()
        api = self.ctx(site).api
        named = answers.get("title") or answers.get("name") or what.noun

        def done(_made: object) -> None:
            state = " as a draft" if what.family == "items" else ""
            self.say(f"Made the {what.noun} {named} on {site}{state}.")
            self.refresh()

        self.background(f"making a {what.noun}", lambda: create(api, what, answers), done)

    # -- terms --------------------------------------------------------------------

    @staticmethod
    def _taxonomy(row: WbRow) -> str:
        if row.subkind:
            return row.subkind
        base = row.route.rsplit("/", 2)[-2] if row.route.count("/") >= 2 else ""
        return _TAXONOMY_OF_ROUTE.get(base, base)

    def do_merge_into(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "term":
            self.say("Merge Into works on a category, tag or term.")
            return
        others = [r for r in self.frame.rows if isinstance(r, WbRow) and r.key != row.key]
        if not others:
            self.say("There is no other term here to merge into.")
            return
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title=f"Merge {row.title} Into",
            prompt="&Into:",
            rows=[r.title for r in others],
            help_text=f"Everything filed under {row.title} is filed under the one you choose, "
            f"then {row.title} is deleted.",
        )
        if index is None:
            return
        target = others[index]
        api, taxonomy = self.ctx(row.site).api, self._taxonomy(row)

        def previewed(preview: Any) -> None:
            if not wdlg.ask_preview(
                self.parent,
                self.show_modal,
                title=f"Merge {row.title} Into {target.title}",
                summary=preview.sentence,
                lines=[f"{route.rsplit('/', 1)[-1]} {ident}" for route, ident in preview.items],
                yes="Merge",
            ):
                return

            def done(failed: list[int]) -> None:
                if failed:
                    self.say(
                        f"{len(failed)} items could not be moved, so {row.title} was kept. "
                        "Try again in a moment."
                    )
                else:
                    self.say(f"Merged {row.title} into {target.title}.")
                self.refresh()

            self.background(
                "merging",
                lambda: merge_terms(api, taxonomy, row.object_id, target.object_id, preview),
                done,
            )

        self.background(
            "counting what moves",
            lambda: merge_preview(
                api, taxonomy, (row.object_id, row.title), (target.object_id, target.title)
            ),
            previewed,
        )

    def do_convert_term(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "term":
            self.say("Convert works on a category or a tag.")
            return
        taxonomy = self._taxonomy(row)
        if taxonomy not in ("category", "post_tag"):
            self.say("Only a category becomes a tag, or a tag a category.")
            return
        target = "category" if taxonomy == "post_tag" else "post_tag"
        word = "category" if target == "category" else "tag"
        if not dlg.confirm(
            self.parent,
            self.show_modal,
            title=f"Make {row.title} a {word.title()}",
            message=f"Make {row.title} a {word} on {row.site}? Every post filed under it "
            f"moves to the {word}, and the old one is deleted.",
            yes_label="Convert",
        ):
            return
        api = self.ctx(row.site).api

        def done(result: tuple[int, list[int]]) -> None:
            _new, failed = result
            if failed:
                self.say(f"{len(failed)} posts could not be moved, so {row.title} was kept.")
            else:
                self.say(f"{row.title} is now a {word}.")
            self.refresh()

        self.background(
            "converting", lambda: convert_term(api, dict(row.raw), taxonomy, target), done
        )

    # -- people -------------------------------------------------------------------

    def do_send_password_reset(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "user":
            self.say("Choose a person in Users first.")
            return
        profile = self.profile(row.site)
        if profile is None:
            return
        address, sentence = password_reset_pointer(profile.site_url, row.object_id, row.title)
        self.say(sentence)
        opener = getattr(getattr(self, "commands", None), "host", None)
        if opener is not None and hasattr(opener, "open_in_browser"):
            opener.open_in_browser(address)
        else:
            import webbrowser

            webbrowser.open(address)

    def do_roles(self, _ref: Any, _row: WbRow | None) -> None:
        lines = [f"{name}: {words}" for name, words in role_rows()]
        dlg.show_report(
            self.parent,
            self.show_modal,
            title="Roles and What They May Do",
            text="\n\n".join([*lines, ROLES_CANNOT_CHANGE]),
            help_text="Each of WordPress's roles in plain words, read only. A site's own "
            "roles, from a role plugin, are not listed.",
        )

    # -- spam ---------------------------------------------------------------------

    def do_empty_spam(self, ref: Any, _row: WbRow | None) -> None:
        site = self.site_of(ref) or self.current_site()
        if not site:
            self.say("Choose a site first.")
            return
        api = self.ctx(site).api

        def counted(ids: list[int]) -> None:
            if not ids:
                self.say(f"No comments are held as spam on {site}.")
                return
            if not dlg.confirm(
                self.parent,
                self.show_modal,
                title="Empty Spam",
                message=f"Delete all {len(ids)} comments held as spam on {site} permanently? "
                "This cannot be undone.",
                yes_label="Delete All",
            ):
                return

            def done(failed: list[int]) -> None:
                gone = len(ids) - len(failed)
                more = f" {len(failed)} could not be deleted." if failed else ""
                self.say(f"Deleted {gone} spam comments on {site}.{more}")
                self.refresh()

            self.background("emptying spam", lambda: empty_spam(api, ids), done)

        self.background("counting spam", lambda: spam_comments(api), counted)

    def do_allow_sender(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "comment":
            self.say("Allow This Sender works on a comment.")
            return
        api = self.ctx(row.site).api
        author = row.cell("author") or "This person"

        def work() -> str:
            set_comment_status(api, row, "approve")
            try:
                settings = admin.load_settings(api)
            except Exception:  # noqa: BLE001 - the approval stands; the words fall back
                settings = {}
            return allow_sender_words(author, settings)

        def done(sentence: str) -> None:
            self.say(sentence)
            self.refresh()

        self.background("allowing the sender", work, done)
