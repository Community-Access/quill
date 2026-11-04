"""Style Variations and Site Styles, the safe subset (wordpress.md 9.15).

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands`. The
thinking is in :mod:`quill.core.wordpress.site_styles`; this module asks,
confirms by name, and speaks the outcome. Every change keeps the look it
replaces on this computer first, so Put Back the Previous Look can restore it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from quill.core.wordpress import site as wp
from quill.core.wordpress import site_features as sf
from quill.core.wordpress import site_styles as ss
from quill.ui import wordpress_dialogs as dlg
from quill.ui.wordpress_api_site_base import WordPressApiSiteBase, plain_error, role_cannot

if TYPE_CHECKING:
    from quill.core.wordpress import sites as st


def _no_theme_sentence(site_name: str, theme: ss.ActiveTheme) -> str:
    name = theme.name or "The active theme"
    return (
        f"{name} on {site_name} is not a block theme, so its look is set in the theme's own "
        "options rather than through WordPress."
    )


class WordPressLookCommands(WordPressApiSiteBase):
    # ------------------------------------------------------------------ #
    # Style Variations

    def cmd_style_variations(self) -> None:
        profile = self.chosen_site("Style Variations")
        if profile is None:
            return

        def why_not(index: sf.SiteIndex, account: wp.Account) -> str:
            if not index.has_route(ss.VARIATIONS_ROUTE):
                return (
                    f"{profile.name} has no style variations to offer. They come with block "
                    "themes, in WordPress 6.2 or later."
                )
            return role_cannot(
                profile.name, account, "edit_theme_options", "change the site's look"
            )

        def work(api: Any, _index: sf.SiteIndex, _account: wp.Account) -> Any:
            theme = ss.active_theme(api)
            if not theme.stylesheet or not theme.block_theme:
                return theme, [], []
            variations = ss.list_variations(api, theme.stylesheet)
            base = ss.theme_styles(api, theme.stylesheet)
            return theme, variations, [ss.variation_report(v, base) for v in variations]

        self.when_offered(
            profile,
            f"reading {profile.name}'s style variations",
            why_not,
            work,
            lambda found: self._show_variations(profile, *found),
        )

    def _show_variations(
        self,
        profile: st.SiteProfile,
        theme: ss.ActiveTheme,
        variations: list[ss.Variation],
        reports: list[list[str]],
    ) -> None:
        if not theme.stylesheet or not theme.block_theme:
            self.host.announce(_no_theme_sentence(profile.name, theme))
            return
        if not variations:
            self.host.announce(
                f"{theme.name or 'The theme'} on {profile.name} has no style variations."
            )
            return
        api = self.api(profile)  # type: ignore[attr-defined]
        rows = [
            f"{v.title}: {ss.report_summary(r)}" for v, r in zip(variations, reports, strict=True)
        ]

        def details(index: int) -> str:
            lines = reports[index]
            return "\n".join(lines) if lines else "No colours QUILL can read in this look."

        def apply(index: int | None) -> object:
            if index is None or index >= len(variations):
                return None
            variation = variations[index]
            if not theme.styles_id:
                self.host.announce(f"{profile.name} did not say where its styles are kept.")
                return None
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Apply Style Variation",
                message=(
                    f"Change the look of {profile.name} to {variation.title}? Visitors see it at "
                    "once. QUILL keeps the current look on this computer, so Put Back the "
                    "Previous Look can restore it."
                ),
                yes_label=f"Apply {variation.title}",
            ):
                return None
            self._change_look(
                profile,
                api,
                theme.styles_id,
                f"applying {variation.title}",
                lambda: ss.apply_variation(api, theme.styles_id, variation),
                f"{variation.title} applied on {profile.name}. Put Back the Previous Look "
                "restores the old one.",
            )
            return None

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title=f"Style Variations, {profile.name}",
            purpose=(
                f"The ready-made looks of {theme.name or 'the theme'} on {profile.name}, each with "
                "its Palette Report, so you can choose one whose colours pass."
            ),
            list_label="&Variations:",
            list_help="Each look's name, and how many of its colour pairings are too faint.",
            rows=rows,
            details=details,
            actions=[
                dlg.Action("&Apply...", "Make the selected look the site's own.", apply),
                self._put_back_action(profile, api, theme.styles_id),
            ],
        )
        window.Destroy()

    # ------------------------------------------------------------------ #
    # Site Styles, the safe subset

    def cmd_site_styles(self) -> None:
        profile = self.chosen_site("Site Styles")
        if profile is None:
            return

        def why_not(index: sf.SiteIndex, account: wp.Account) -> str:
            if not index.has_route(ss.STYLES_ROUTE):
                return (
                    f"{profile.name} does not offer its site styles. They come with block themes, "
                    "in WordPress 5.9 or later."
                )
            return role_cannot(
                profile.name, account, "edit_theme_options", "change the site's look"
            )

        def work(api: Any, _index: sf.SiteIndex, _account: wp.Account) -> Any:
            theme = ss.active_theme(api)
            if not theme.stylesheet or not theme.styles_id:
                return theme, {}, {}
            return (
                theme,
                ss.theme_styles(api, theme.stylesheet),
                ss.load_user_styles(api, theme.styles_id),
            )

        self.when_offered(
            profile,
            f"reading {profile.name}'s site styles",
            why_not,
            work,
            lambda found: self._show_styles(profile, *found),
        )

    def _show_styles(
        self,
        profile: st.SiteProfile,
        theme: ss.ActiveTheme,
        base: dict[str, Any],
        user: dict[str, Any],
    ) -> None:
        if not theme.stylesheet or not theme.styles_id:
            self.host.announce(_no_theme_sentence(profile.name, theme))
            return
        if not ss.entries(base, user):
            self.host.announce(
                f"{theme.name or 'The theme'} on {profile.name} sets no colours or font sizes."
            )
            return
        api = self.api(profile)  # type: ignore[attr-defined]
        live = {"user": user}

        def rows() -> list[str]:
            background, text = ss.page_colours(base, live["user"])
            return [ss.entry_row(e, background, text) for e in ss.entries(base, live["user"])]

        def change(index: int | None) -> object:
            found = ss.entries(base, live["user"])
            if index is None or index >= len(found):
                return None
            entry = found[index]
            value = self._ask_style_value(entry)
            if value is None or value == entry.value:
                return None
            if entry.kind == "colour":
                background, text = ss.page_colours(base, live["user"])
                said = ss.contrast_sentence(entry.name, value, background, text)
                message = (
                    f"Change {entry.name} on {profile.name} from {entry.value} to {value}? {said}."
                )
            else:
                message = (
                    f"Change the {entry.name} font size on {profile.name} from {entry.value} "
                    f"to {value}?"
                )
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Change Site Style",
                message=message + " Visitors see it at once.",
                yes_label=f"Change {entry.name}",
            ):
                return None
            before = dict(live["user"])
            settings = ss.changed_settings(base, before, entry, value)
            live["user"] = {**before, "settings": settings}
            self._change_look(
                profile,
                api,
                theme.styles_id,
                f"changing {entry.name}",
                lambda: ss.save_user_styles(api, theme.styles_id, {"settings": settings}),
                f"{entry.name} changed on {profile.name}.",
                before=before,
            )
            return rows()

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title=f"Site Styles, {profile.name}",
            purpose=(
                f"The colours and font sizes of {profile.name}, by name. Each colour says its "
                "contrast on the page background. Everything else about the look stays in the "
                "Site Editor."
            ),
            list_label="&Styles:",
            list_help="Each colour with its contrast, then each font size.",
            rows=rows(),
            actions=[
                dlg.Action("&Change...", "Change the selected colour or font size.", change),
                self._put_back_action(profile, api, theme.styles_id),
            ],
        )
        window.Destroy()

    def _ask_style_value(self, entry: ss.StyleEntry) -> str | None:
        colour = entry.kind == "colour"
        typed = dlg.ask_text(
            self.host.parent,
            self.host.show_modal,
            title=f"Change {entry.name}",
            prompt="&Colour:" if colour else "&Size:",
            value=entry.value,
            help_text=(
                "A hex colour such as #1a4d2e, or rgb(26, 77, 46). Before anything is saved, "
                "QUILL says how it reads on the page background."
                if colour
                else "A size with its unit, such as 1.125rem or 18px."
            ),
        )
        if typed is None or not typed.strip():
            return None
        try:
            return ss.check_colour(typed) if colour else ss.check_size(typed)
        except ss.StyleValueError as exc:
            self.host.announce(plain_error(exc))
            return None

    # ------------------------------------------------------------------ #
    # Keeping the look before a change, and putting it back

    def _change_look(
        self,
        profile: st.SiteProfile,
        api: Any,
        styles_id: int,
        doing: str,
        change: Any,
        said: str,
        *,
        before: dict[str, Any] | None = None,
    ) -> None:
        root = self.local.root  # type: ignore[attr-defined]

        def job() -> None:
            current = before if before is not None else ss.load_user_styles(api, styles_id)
            ss.keep_previous(root, profile.id, current, reason=doing)
            change()

        self.background(doing, job, lambda _r: self.host.announce(said))  # type: ignore[attr-defined]

    def _put_back_action(self, profile: st.SiteProfile, api: Any, styles_id: int) -> dlg.Action:
        root = self.local.root  # type: ignore[attr-defined]

        def put_back(_index: int | None) -> object:
            saved = ss.previous(root, profile.id)
            if saved is None:
                self.host.announce(f"QUILL has no earlier look kept for {profile.name}.")
                return None
            when = wp.friendly_date(str(saved.get("saved_at", "")))
            reason = str(saved.get("reason", "") or "the last change")
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Put Back the Previous Look",
                message=f"Put back the look {profile.name} had before {reason}, kept {when}?",
                yes_label="Put Back",
            ):
                return None
            self.background(  # type: ignore[attr-defined]
                "putting back the previous look",
                lambda: ss.put_back(api, styles_id, saved),
                lambda _r: self.host.announce(f"The previous look is back on {profile.name}."),
            )
            return None

        return dlg.Action(
            "Put &Back the Previous Look...",
            "Restore the look the site had before QUILL last changed it.",
            put_back,
            needs_row=False,
        )
