"""Event categories and tags, Yoast SEO's Edit SEO with social fields, and the Bulk SEO Editor.

A mixin on :class:`quill.ui.wordpress_workbench_shop_setup.WorkbenchShopSetupCommands`;
the words and checks are wx-free in
:mod:`quill.core.wordpress.workbench_event_terms`,
:mod:`quill.core.wordpress.workbench_seo` and
:mod:`quill.core.wordpress.workbench_seo_bulk`. Edit SEO writes each field
through the post meta Yoast registers for REST where it does, and otherwise
through Yoast's own bulk editor routes; what neither reaches is named and
left for the item's Yoast panel. The Bulk SEO Editor is a list of posts and
pages whose SEO title and description are changed where they stand, one item
at a time, each previewed, checked against the site, verified and undoable.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.wordpress import workbench_event_terms as terms
from quill.core.wordpress import workbench_seo as seo
from quill.core.wordpress import workbench_seo_bulk as bulk
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.plugin_events import NAMESPACE, EventDateError
from quill.core.wordpress.workbench_edit import EditConflict
from quill.core.wordpress.workbench_plugin_write import checked_write
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.history import Change
from quill.ui import wordpress_dialogs as dlg
from quill.ui.wordpress_workbench_shop_setup import WorkbenchShopSetupCommands

_SEO_PROMPTS = (
    ("seo_title", "_yoast_wpseo_title", "SEO &title:", "About 60 characters show in results."),
    ("meta_description", "_yoast_wpseo_metadesc", "Meta &description:", "About 160 show."),
    ("focus_keyphrase", "_yoast_wpseo_focuskw", "&Focus keyphrase:", "The words to be found by."),
    (
        "social_title",
        "_yoast_wpseo_opengraph-title",
        "&Social title:",
        "The title shown when the item is shared on social media; blank uses the SEO title.",
    ),
    (
        "social_description",
        "_yoast_wpseo_opengraph-description",
        "Social d&escription:",
        "The words shown when it is shared; blank uses the meta description.",
    ),
    (
        "",
        "_yoast_wpseo_opengraph-image",
        "Social &image address:",
        "The address of the picture shown when it is shared.",
    ),
)


class WorkbenchTermsSeoCommands(WorkbenchShopSetupCommands):
    """Event categories and tags, and Yoast SEO."""

    # -- event categories and tags --------------------------------------------------------

    def _new_event_term(self, ref: Any, row: WbRow | None, kind: str) -> None:
        site = self._shop_site(ref, row)
        if not site or not self._may_change(site):
            return
        noun = terms.TERM_KINDS[kind][1]
        name = self._pl_ask(f"New {noun.title()}", "&Name:", f"The {noun}'s name.")
        if name is None or not name.strip():
            return
        if not self._pl_preview(
            f"New {noun.title()}",
            f"Make the {noun} {name.strip()} on {site}.",
            [
                f"A new {noun} on {site}: {name.strip()}.",
                "Categories and Tags on an event gives it to that event. Ctrl+Z deletes it again.",
            ],
            "Make It",
        ):
            return
        api = self.ctx(site).api  # type: ignore[attr-defined]
        base = terms.route(kind)

        def done(answer: Any) -> None:
            made = answer.get("id") if isinstance(answer, dict) else None
            said = f"Made the {noun} {name.strip()} on {site}."
            undo = None
            if made:
                undo = lambda: (api.delete(f"{base}/{made}"), f"Deleted the {noun} again.")[1]  # noqa: E731
            self.history.record(Change(f"{site}: {name.strip()}", said, undo=undo))  # type: ignore[attr-defined]
            self.say(said)  # type: ignore[attr-defined]
            self.refresh()  # type: ignore[attr-defined]

        self.background(f"making the {noun}", lambda: api.post(base, {"name": name.strip()}), done)  # type: ignore[attr-defined]

    def do_new_event_category(self, ref: Any, row: WbRow | None) -> None:
        self._new_event_term(ref, row, "tribe_category")

    def do_new_event_tag(self, ref: Any, row: WbRow | None) -> None:
        self._new_event_term(ref, row, "tribe_tag")

    def do_rename_event_term(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind not in terms.TERM_KINDS:
            return
        noun = terms.TERM_KINDS[row.kind][1]
        name = self._pl_ask(f"Rename - {row.title}", "&New name:", f"The {noun}'s name.", row.title)
        if name is None or name.strip() in ("", row.title):
            return
        if not self._pl_preview(
            "Rename",
            f"Rename the {noun} {row.title} on {row.site}.",
            [f"{row.title} becomes {name.strip()}.", "Its events keep it under the new name."],
            "Rename",
        ):
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        route, body = terms.route(row.kind, row.object_id), {"name": name.strip()}
        self._pl_checked(
            row.site,
            f"renaming {row.title}",
            lambda: checked_write(
                api, route, body, row.raw.get("_loaded", {}), name=row.title, site=row.site
            ),
            f"Renamed the {noun} {row.title} to {name.strip()} on {row.site}.",
            lambda w: self._pl_undo(api, route, dict(w.undo), f"Named it {row.title} again."),
        )

    def do_delete_event_term(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind not in terms.TERM_KINDS:
            return
        noun = terms.TERM_KINDS[row.kind][1]
        if not self._pl_preview(
            f"Delete {noun.title()}",
            f"Delete the {noun} {row.title} on {row.site} for good.",
            [row.detail, "There is no Trash: its events lose it, and keep everything else."],
            "Delete",
        ):
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        self._pl_send(
            row.site,
            f"deleting {row.title}",
            lambda: api.delete(terms.route(row.kind, row.object_id)),
            f"Deleted the {noun} {row.title} on {row.site}.",
        )

    def do_set_event_terms(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "tribe_event" or self._recurring_refused(row):  # type: ignore[attr-defined]
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        route = f"{NAMESPACE}/events/{row.object_id}"

        def read() -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
            event = api.get(route)
            return (
                event if isinstance(event, dict) else {},
                terms.collect_terms(api, "categories", {"hide_empty": False}),
                terms.collect_terms(api, "tags", {"hide_empty": False}),
            )

        def chosen(
            found: tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]],
        ) -> None:
            event, cats, tags = found
            old = {
                "categories": terms.term_names(event.get("categories")),
                "tags": terms.term_names(event.get("tags")),
            }
            title = f"Categories and Tags - {row.title}"
            new_cats = self._pl_ask(
                title,
                "&Categories (a comma between):",
                "The calendar's own category names.",
                old["categories"],
            )
            if new_cats is None:
                return
            new_tags = self._pl_ask(
                title, "&Tags (a comma between):", "The calendar's tag names.", old["tags"]
            )
            if new_tags is None:
                return
            try:
                body = {
                    "categories": terms.terms_by_name(new_cats, cats, "event category"),
                    "tags": terms.terms_by_name(new_tags, tags, "event tag"),
                }
            except EventDateError as exc:
                self.say(f"{exc} Nothing was changed.")  # type: ignore[attr-defined]
                return
            before = {k: terms.event_term_ids(event, k) for k in body}
            changed = [k for k in body if sorted(body[k]) != before[k]]
            if not changed:
                self.say(f"{row.title}'s categories and tags would not change.")  # type: ignore[attr-defined]
                return
            body = {k: body[k] for k in changed}
            new = {"categories": new_cats.strip(), "tags": new_tags.strip()}
            if not self._pl_preview(
                "Categories and Tags",
                f"Change {row.title} on {row.site}.",
                terms.terms_preview(row.title, row.site, old, new, changed),
                "Change Event",
            ):
                return

            def work() -> dict[str, Any]:
                now = api.get(route)
                now = now if isinstance(now, dict) else {}
                moved = [k for k in body if terms.event_term_ids(now, k) != before[k]]
                if moved:
                    raise EditConflict(
                        f"{row.title}'s {' and '.join(moved)} changed on {row.site} after QUILL "
                        "read them. Nothing was sent. F5 reads it again."
                    )
                answer = api.post(route, body)
                return answer if isinstance(answer, dict) else {}

            def done(answer: dict[str, Any]) -> None:
                missed = [
                    k for k in body if answer and terms.event_term_ids(answer, k) != sorted(body[k])
                ]
                said = f"Changed {row.title}'s {' and '.join(changed)} on {row.site}." + (
                    f" The site did not keep: {', '.join(missed)}." if missed else ""
                )
                back = {k: before[k] for k in body}
                undo = lambda: (api.post(route, back), f"Put {row.title}'s terms back.")[1]  # noqa: E731
                self.history.record(Change(f"{row.site}: {row.title}", said, undo=undo))  # type: ignore[attr-defined]
                self.say(said)  # type: ignore[attr-defined]
                self.refresh()  # type: ignore[attr-defined]

            self.background(f"changing {row.title}", work, done)  # type: ignore[attr-defined]

        self.background(f"reading {row.title}", read, chosen)  # type: ignore[attr-defined]

    # -- Yoast SEO ------------------------------------------------------------------------

    def do_search_appearance(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "seo_item":
            return
        self._pl_report(
            f"Search Appearance - {row.title}",
            str(row.raw.get("appearance", "")),
            "The title, address and description a search engine shows, as Yoast gives them.",
        )

    def _read_yoast(self, row: WbRow) -> Callable[[], dict[str, Any]]:
        ctx = self.ctx(row.site)  # type: ignore[attr-defined]

        def read() -> dict[str, Any]:
            if not bulk.has_bulk_editor(ctx):
                return {}
            try:
                found = bulk.read_bulk(
                    ctx.api, row.site, row.subkind or "post", ids=[row.object_id]
                )
            except WordPressApiError as exc:
                if exc.status in (401, 403, 404):
                    return {}
                raise
            return found[0] if found else {}

        return read

    def do_edit_seo(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "seo_item":
            return
        self.background(
            f"reading {row.title}'s SEO",
            self._read_yoast(row),  # type: ignore[attr-defined]
            lambda post: self._edit_seo(row, post),
        )

    def _edit_seo(self, row: WbRow, post: dict[str, Any]) -> None:
        meta = dict(row.raw.get("meta") or {})
        title = f"Edit SEO - {row.title}"
        wanted_meta: dict[str, str] = {}
        wanted_bulk: dict[str, str] = {}
        for name, key, prompt, help_text in _SEO_PROMPTS:
            value = meta.get(key) if key in meta else (post.get(name, "") if name else "")
            text = self._pl_ask(title, prompt, help_text, str(value or ""))
            if text is None:
                return
            if key in meta or not name or not post:
                wanted_meta[key] = text
            else:
                wanted_bulk[name] = text
        values = list(seo.NOINDEX)
        picked = self._pl_choose(
            title,
            "Show in search &results:",
            [seo.NOINDEX[v] for v in values],
            "Whether search engines may list it.",
        )
        if picked is None:
            return
        edit = seo.SeoEdit(
            wanted_meta.get("_yoast_wpseo_title"),
            wanted_meta.get("_yoast_wpseo_metadesc"),
            wanted_meta.get("_yoast_wpseo_focuskw"),
            values[picked],
        )
        body, unwritable = seo.seo_body(meta, edit)
        social, social_unwritable = bulk.meta_social(meta, wanted_meta)
        body.update(social)
        unwritable += social_unwritable
        search_part, social_part = bulk.split_changes(post, wanted_bulk)
        changes = {**search_part, **social_part}
        if not body and not changes:
            said = f"Nothing about {row.title}'s SEO would change."
            if unwritable:
                said += f" {', '.join(unwritable)} cannot be written here; Yoast's panel does it."
            self.say(said)  # type: ignore[attr-defined]
            return
        lines = seo.seo_preview(
            row.title,
            row.site,
            meta,
            {k: v for k, v in body.items() if k in seo.SEO_META},
            unwritable,
        )
        lines[1:1] = [
            f"{bulk.SOCIAL_META[k]}: {meta.get(k) or 'not set'} becomes {v or 'not set'}."
            for k, v in social.items()
        ]
        if changes:
            lines[1:1] = bulk.change_lines(row.title, post, changes)[1:]
        if not self._pl_preview(
            "Edit SEO", f"Change Yoast SEO for {row.title} on {row.site}.", lines, "Change SEO"
        ):
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        route = str(row.raw.get("route", ""))
        kind = row.subkind or "post"

        def work() -> tuple[tuple[str, ...], dict[str, Any], dict[str, str]]:
            missed: tuple[str, ...] = ()
            meta_undo: dict[str, Any] = {}
            bulk_undo: dict[str, str] = {}
            if body:
                written = checked_write(
                    api, route, {"meta": body}, {"meta": meta}, name=row.title, site=row.site
                )
                missed += written.not_kept
                meta_undo = dict(written.undo)
            if changes:
                _now, kept_not, bulk_undo = bulk.save_bulk(
                    api, row.site, kind, row.object_id, post, changes
                )
                missed += kept_not
            return missed, meta_undo, bulk_undo

        def done(result: tuple[tuple[str, ...], dict[str, Any], dict[str, str]]) -> None:
            missed, meta_undo, bulk_undo = result
            said = f"Changed Yoast SEO for {row.title} on {row.site}." + (
                f" The site did not keep: {', '.join(missed)}." if missed else ""
            )

            def undo() -> str:
                if meta_undo:
                    api.post(route, meta_undo)
                if bulk_undo:
                    bulk.put_back(api, row.site, row.object_id, bulk_undo)
                return f"Put {row.title}'s SEO back."

            self.history.record(Change(f"{row.site}: {row.title}", said, undo=undo))  # type: ignore[attr-defined]
            self.say(said)  # type: ignore[attr-defined]
            self.refresh()  # type: ignore[attr-defined]

        self.background(f"changing {row.title}'s SEO", work, done)  # type: ignore[attr-defined]

    # -- the Bulk SEO Editor -----------------------------------------------------------------

    def do_bulk_seo(self, ref: Any, row: WbRow | None) -> None:
        site = self._shop_site(ref, row)
        if not site:
            return
        ctx = self.ctx(site)  # type: ignore[attr-defined]
        if not bulk.has_bulk_editor(ctx):
            self.say(f"{site}'s Yoast SEO has no bulk editor routes; it came with Yoast SEO 28.")  # type: ignore[attr-defined]
            return

        def read() -> list[tuple[str, dict[str, Any]]]:
            found: list[tuple[str, dict[str, Any]]] = []
            for kind in ("post", "page"):
                found += [(kind, p) for p in bulk.read_bulk(ctx.api, site, kind)]
            return found

        self.background(f"reading {site}'s SEO", read, lambda posts: self._bulk_window(site, posts))  # type: ignore[attr-defined]

    def _bulk_window(self, site: str, posts: list[tuple[str, dict[str, Any]]]) -> None:
        if not posts:
            self.say(f"Yoast SEO's bulk editor gave no posts or pages on {site}.")  # type: ignore[attr-defined]
            return
        holder: dict[str, Any] = {}

        def lines() -> list[str]:
            return [bulk.bulk_line(p) for _k, p in posts]

        def edit(index: int | None) -> object:
            if index is not None:
                self._bulk_edit_one(site, posts, index, lambda: _refresh(holder, lines(), index))
            return None

        window = dlg.ListWindow(
            self.parent,  # type: ignore[attr-defined]
            title=f"Bulk SEO Editor - {site}",
            purpose="Every post and page with its Yoast SEO title and description. Enter changes "
            "the selected one where it stands, after a preview; Ctrl+Z in the Workbench undoes it.",
            list_label="&Posts and pages:",
            list_help="Each item's title and how long its SEO title and description are. Enter "
            "changes them.",
            rows=lines(),
            actions=[
                dlg.Action(
                    "&Change SEO Title and Description...",
                    "Change the selected item's SEO title and description. Enter.",
                    edit,
                )
            ],
            details=lambda i: bulk.bulk_details(posts[i][1]),
            on_enter=edit,
        )
        holder["window"] = window
        try:
            self.show_modal(window, f"Bulk SEO Editor - {site}")  # type: ignore[attr-defined]
        finally:
            holder.pop("window", None)
            window.Destroy()

    def _bulk_edit_one(
        self,
        site: str,
        posts: list[tuple[str, dict[str, Any]]],
        index: int,
        shown: Callable[[], None],
    ) -> None:
        kind, post = posts[index]
        name = str(post.get("title", "") or "this item")
        if not post.get("editable", True):
            self.say(f"Your role cannot edit {name}, so Yoast keeps its SEO locked.")  # type: ignore[attr-defined]
            return
        title = f"Edit SEO - {name}"
        wanted: dict[str, str] = {}
        for key, prompt, help_text in (
            ("seo_title", "SEO &title:", "About 60 characters show in results."),
            ("meta_description", "Meta &description:", "About 160 characters show."),
        ):
            text = self._pl_ask(title, prompt, help_text, str(post.get(key, "") or ""))
            if text is None:
                return
            wanted[key] = text
        search, social = bulk.split_changes(post, wanted)
        changes = {**search, **social}
        if not changes:
            self.say(f"Nothing about {name}'s SEO would change.")  # type: ignore[attr-defined]
            return
        if not self._pl_preview(
            "Bulk SEO Editor",
            f"Change Yoast SEO for {name} on {site}.",
            bulk.change_lines(name, post, changes),
            "Change SEO",
        ):
            return
        api = self.ctx(site).api  # type: ignore[attr-defined]
        post_id = int(post.get("id", 0) or 0)

        def done(result: tuple[dict[str, Any], tuple[str, ...], dict[str, str]]) -> None:
            now, missed, undo_fields = result
            posts[index] = (kind, {**post, **changes, **(now or {})})
            said = f"Changed Yoast SEO for {name} on {site}." + (
                f" The site did not keep: {', '.join(missed)}." if missed else ""
            )

            def undo() -> str:
                bulk.put_back(api, site, post_id, undo_fields)
                return f"Put {name}'s SEO back."

            self.history.record(Change(f"{site}: {name}", said, undo=undo))  # type: ignore[attr-defined]
            self.say(said)  # type: ignore[attr-defined]
            shown()

        self.background(
            f"changing {name}'s SEO",  # type: ignore[attr-defined]
            lambda: bulk.save_bulk(api, site, kind, post_id, post, changes),
            done,
        )


def _refresh(holder: dict[str, Any], rows: list[str], keep: int) -> None:
    window = holder.get("window")
    if window is not None:
        try:
            window.set_rows(rows, keep=keep)
        except RuntimeError:  # the window closed while the save ran
            holder.pop("window", None)
