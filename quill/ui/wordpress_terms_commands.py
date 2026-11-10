"""Categories and Tags (wordpress.md 9.13): add, rename, merge, convert, tidy, default.

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands`, gathered
by :class:`~quill.ui.wordpress_admin_commands.WordPressAdminCommands`.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any

from quill.core.wordpress import site as wp
from quill.core.wordpress import site_admin as sa
from quill.core.wordpress import site_library as lib
from quill.ui import wordpress_dialogs as dlg
from quill.ui.wordpress_admin_base import WordPressAdminBase

if TYPE_CHECKING:
    from quill.core.wordpress import sites as st


class WordPressTermsCommands(WordPressAdminBase):
    def cmd_manage_terms(self) -> None:
        if self.workbench_door("wordpress.manage_terms"):
            return  # the developer flag sends this door to the WordPress Workbench
        profile = self.admin_site("Categories and Tags")
        if profile is None:
            return
        which = dlg.ask_choice(
            self.host.parent,
            self.host.show_modal,
            title="Categories and Tags",
            prompt="&Manage:",
            rows=["Categories", "Tags"],
            help_text="Categories are broad groups; tags are specific subjects.",
        )
        if which is None:
            return
        self._load_terms(profile, "category" if which == 0 else "post_tag")

    def _load_terms(self, profile: st.SiteProfile, taxonomy: str) -> None:
        def work(api: Any, account: wp.Account) -> tuple[list[wp.Term], int]:
            default = lib.default_category(api) if account.can_manage_options else 0
            return wp.list_terms(api, taxonomy), default

        self.admin_load(
            profile,
            "reading categories and tags",
            "terms",
            work,
            lambda api, account, data: self._show_terms(
                profile, api, account, taxonomy, data[0], data[1]
            ),
        )

    def _show_terms(
        self,
        profile: st.SiteProfile,
        api: Any,
        account: wp.Account,
        taxonomy: str,
        terms: list[wp.Term],
        default_id: int = 0,
    ) -> None:
        live = list(terms)
        noun = "category" if taxonomy == "category" else "tag"
        other = "tag" if noun == "category" else "category"
        nouns = "categories" if noun == "category" else "tags"
        default = [default_id]

        def name_of(term_id: int) -> str:
            return next((t.name for t in live if t.id == term_id), "")

        def rows() -> list[str]:
            out = []
            for t in live:
                parent = f", under {name_of(t.parent)}" if t.parent and name_of(t.parent) else ""
                mark = ", the default" if t.id == default[0] and noun == "category" else ""
                out.append(f"{t.name}, {t.slug}, {t.count} posts{parent}{mark}")
            return out

        def at(index: int | None) -> wp.Term | None:
            return live[index] if index is not None and index < len(live) else None

        def add(_i: int | None) -> object:
            name = dlg.ask_text(
                self.host.parent,
                self.host.show_modal,
                title=f"New {noun.title()}",
                prompt="&Name:",
                help_text=f"The new {noun}'s name. WordPress makes its slug from it.",
            )
            if name and name.strip():

                def done(term: wp.Term) -> None:
                    live.append(term)
                    self.host.announce(f"{noun.title()} {term.name} added to {profile.name}.")

                self.background("adding", lambda: wp.create_term(api, taxonomy, name.strip()), done)  # type: ignore[attr-defined]
            return None

        def rename(index: int | None) -> object:
            term = at(index)
            if term is None:
                return None
            name = dlg.ask_text(
                self.host.parent,
                self.host.show_modal,
                title=f"Rename {noun.title()}",
                prompt="&Name:",
                value=term.name,
                help_text=f"The {noun}'s new name.",
            )
            if not name or not name.strip() or name.strip() == term.name:
                return None
            updated = replace(term, name=name.strip())
            self.site_job(
                "renaming",
                lambda: wp.update_term(api, updated),
                lambda _t: f"Renamed to {updated.name} on {profile.name}.",
            )
            live[live.index(term)] = updated
            return rows()

        def delete(index: int | None) -> object:
            term = at(index)
            if term is None:
                return None
            if noun == "category" and term.id == default[0]:
                self.host.announce(
                    f"{term.name} is the default category on {profile.name}, so WordPress "
                    "keeps it. Choose another default first."
                )
                return None
            fallback = (
                f" Posts with no other category go to {name_of(default[0])}."
                if noun == "category" and name_of(default[0])
                else ""
            )
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title=f"Delete {noun.title()}",
                message=(
                    f"Delete the {noun} {term.name} from {profile.name}? "
                    f"{term.count} posts use it; they keep their other {nouns}.{fallback}"
                ),
                yes_label=f"Delete {term.name}",
            ):
                return None
            self.site_job(
                "deleting",
                lambda: wp.delete_term(api, taxonomy, term.id),
                lambda _r: f"{term.name} deleted from {profile.name}.",
            )
            live.remove(term)
            return rows()

        def merge(index: int | None) -> object:
            source = at(index)
            if source is None or len(live) < 2:
                return None
            others = [t for t in live if t.id != source.id]
            target_index = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title=f"Merge {source.name} Into",
                prompt="&Into:",
                rows=[t.name for t in others],
                help_text=(
                    f"Every post in {source.name} moves to the one you choose, "
                    f"then {source.name} is deleted."
                ),
            )
            if target_index is None:
                return None
            target = others[target_index]
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Merge",
                message=(
                    f"Move {source.count} posts from {source.name} to {target.name} "
                    f"on {profile.name}, then delete {source.name}?"
                ),
                yes_label="Merge",
            ):
                return None
            self.site_job(
                "merging",
                lambda: wp.merge_terms(api, taxonomy, source.id, target.id),
                lambda moved: f"{moved} posts moved to {target.name}; {source.name} deleted.",
            )
            live.remove(source)
            return rows()

        def convert(index: int | None) -> object:
            term = at(index)
            if term is None:
                return None
            if noun == "category" and term.id == default[0]:
                self.host.announce(
                    f"{term.name} is the default category, so it cannot become a tag. "
                    "Choose another default first."
                )
                return None
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title=f"Convert to {other.title()}",
                message=(
                    f"Turn the {noun} {term.name} on {profile.name} into a {other}? Its "
                    f"{term.count} posts get the {other} {term.name}, and the {noun} is deleted."
                ),
                yes_label=f"Convert to {other.title()}",
            ):
                return None
            self.site_job(
                f"converting to a {other}",
                lambda: lib.convert_term(api, term),
                lambda result: (
                    f"{term.name} is now a {other} on {profile.name}; {result[1]} posts moved."
                ),
            )
            live.remove(term)
            return rows()

        def find_unused(_i: int | None) -> object:
            spare = lib.unused(live, keep=default[0] if noun == "category" else 0)
            if not spare:
                self.host.announce(f"Every {noun} on {profile.name} is used by a post.")
                return None
            names = ", ".join(t.name for t in spare)
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title=f"Unused {nouns.title()}",
                message=(
                    f"{len(spare)} {nouns} on {profile.name} have no posts: {names}. "
                    "Delete them all?"
                ),
                yes_label=f"Delete {len(spare)}",
            ):
                return None
            self.site_job(
                f"deleting unused {nouns}",
                lambda: lib.delete_terms(api, spare),
                lambda n: f"{n} unused {nouns} deleted from {profile.name}.",
            )
            for t in spare:
                live.remove(t)
            return rows()

        def make_default(index: int | None) -> object:
            term = at(index)
            if term is None or term.id == default[0]:
                return None
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Default Category",
                message=(
                    f"Make {term.name} the default category on {profile.name}? New posts with "
                    "no category chosen go there."
                ),
                yes_label="Make Default",
            ):
                return None
            self.site_job(
                "setting the default category",
                lambda: lib.set_default_category(api, term.id),
                lambda _r: f"{term.name} is now the default category on {profile.name}.",
            )
            default[0] = term.id
            return rows()

        actions = [
            dlg.Action("&Add...", f"Add a new {noun}.", add, needs_row=False),
            dlg.Action("&Rename...", f"Rename the selected {noun}.", rename),
            dlg.Action(
                "&Merge Into...",
                f"Move every post from the selected {noun} to another, then delete it.",
                merge,
            ),
            dlg.Action(
                f"&Convert to {other.title()}...",
                f"Turn the selected {noun} into a {other}, keeping its posts.",
                convert,
            ),
            dlg.Action(
                "Find &Unused...",
                f"Find every {noun} no post uses, and delete them together.",
                find_unused,
                needs_row=False,
            ),
            dlg.Action("&Delete...", f"Delete the selected {noun} from the site.", delete),
        ]
        purpose = f"Every {noun} on {profile.name}, with how many posts use it."
        if noun == "category" and sa.can(account, "settings"):
            actions.append(
                dlg.Action(
                    "Make De&fault...",
                    "Make the selected category the one new posts get when none is chosen.",
                    make_default,
                )
            )
        elif noun == "category":
            purpose += " Only an administrator can change the default category."
        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title=f"{'Categories' if taxonomy == 'category' else 'Tags'} on {profile.name}",
            purpose=purpose,
            list_label="Categorie&s:" if noun == "category" else "Tag&s:",
            list_help=(
                f"Each {noun}'s name, slug, how many posts use it"
                + (", and the category it sits under." if noun == "category" else ".")
            ),
            rows=rows(),
            actions=actions,
        )
        window.Destroy()
