"""Site Check, Site Settings, Plugins and Themes (wordpress.md 9.10, 9.13).

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands`, gathered
by :class:`~quill.ui.wordpress_admin_commands.WordPressAdminCommands`. Every
change is confirmed by name and site.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from quill.core.wordpress import site as wp
from quill.core.wordpress import site_admin as sa
from quill.core.wordpress import site_media as wpm
from quill.ui import wordpress_dialogs as dlg
from quill.ui.wordpress_design_commands import WordPressDesignCommands

if TYPE_CHECKING:
    from quill.core.wordpress import sites as st


class WordPressManageCommands(WordPressDesignCommands):
    # ------------------------------------------------------------------ #
    # Site Check (9.10)

    def cmd_site_check(self) -> None:
        if self.workbench_door("wordpress.site_check"):
            return  # the developer flag sends this door to the WordPress Workbench
        profile = self.admin_site("Site Check")
        if profile is None:
            return

        def show(_api: Any, _account: wp.Account, lines: list[sa.CheckLine]) -> None:
            dlg.show_report(
                self.host.parent,
                self.host.show_modal,
                title=f"Site Check, {profile.name}",
                text=sa.check_text(profile.name, lines),
                help_text=(
                    "What the site says about its own health, critical problems first. Each "
                    "line is one answer."
                ),
            )

        self.admin_load(
            profile,
            f"checking {profile.name}",
            None,
            lambda api, _account: sa.site_check(
                api, site_url=profile.site_url, wp_version=profile.wp_version
            ),
            show,
        )

    # ------------------------------------------------------------------ #
    # Site Settings (9.10, 9.13)

    def cmd_site_settings(self) -> None:
        if self.workbench_door("wordpress.site_settings"):
            return  # the developer flag sends this door to the WordPress Workbench
        profile = self.admin_site("Site Settings")
        if profile is None:
            return

        def work(api: Any, _account: wp.Account) -> tuple[dict[str, Any], list[tuple[int, str]]]:
            params: dict[str, object] = {"status": "publish", "_fields": "id,title"}
            pages = [
                (int(r.get("id", 0)), wp.rendered(r.get("title")) or "(untitled)")
                for r in api.iter_collection("wp/v2/pages", params)
            ]
            return sa.load_settings(api), pages

        self.admin_load(
            profile,
            f"reading {profile.name}'s settings",
            "settings",
            work,
            lambda api, _account, data: self._show_settings(profile, api, *data),
        )

    def _show_settings(
        self,
        profile: st.SiteProfile,
        api: Any,
        settings: dict[str, Any],
        pages: list[tuple[int, str]],
    ) -> None:
        page_names = dict(pages)

        def table() -> list[tuple[str, str, str]]:
            return sa.settings_rows(settings, page_names)

        def rows() -> list[str]:
            return [f"{label}: {value}" for _k, label, value in table()]

        def save(key: str, label: str, value: Any, value_text: str) -> None:
            old_text = sa.settings_value_text(key, settings.get(key), page_names)
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title=f"Change {label}",
                message=(
                    f"Change {label.lower()} on {profile.name} from {old_text} to {value_text}?"
                ),
                yes_label=f"Change {label}",
            ):
                return
            settings[key] = value
            self.site_job(
                f"saving {label.lower()}",
                lambda: sa.save_setting(api, key, value),
                lambda _r: f"{label} on {profile.name} is now {value_text}.",
            )

        def choose(label: str, options: list[tuple[Any, str]], current: Any) -> Any:
            values = [v for v, _n in options]
            picked = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title=label,
                prompt="&Choose:",
                rows=[n for _v, n in options],
                initial=values.index(current) if current in values else 0,
                help_text=f"The new {label.lower()} for {profile.name}.",
            )
            return None if picked is None else options[picked]

        def change(index: int | None) -> object:
            if index is None:
                return None
            key, label, _value = table()[index]
            kind = next(k for f, _l, k in sa.SETTINGS_FIELDS if f == key)
            current = settings.get(key)
            if kind == "media":
                self._choose_site_icon(profile, api, settings, save)
                return None
            if kind in {"choice", "bool", "page"}:
                if kind == "choice":
                    options: list[tuple[Any, str]] = list(sa.CHOICES[key])
                    if key == "start_of_week":
                        options = [(int(v), n) for v, n in options]
                elif kind == "bool":
                    options = [(True, "Yes"), (False, "No")]
                else:
                    options = [(0, "None"), *pages]
                answer = choose(label, options, current)
                if answer is None or answer[0] == current:
                    return None
                save(key, label, answer[0], answer[1])
                return rows()
            text = dlg.ask_text(
                self.host.parent,
                self.host.show_modal,
                title=label,
                prompt=f"&{label}:",
                value="" if current is None else str(current),
                help_text=_SETTING_HELP.get(key, f"The site's {label.lower()}."),
            )
            if text is None or text.strip() == str(current or "").strip():
                return None
            value: Any = text.strip()
            if kind == "number":
                if not value.isdigit() or int(value) < 1:
                    self.host.announce(f"{label} must be a whole number, 1 or more.")
                    return None
                value = int(value)
            save(key, label, value, str(value))
            return rows()

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title=f"Site Settings, {profile.name}",
            purpose=(
                f"{profile.name}'s own settings. The site language matters for accessibility: "
                "it is every page's language, so it decides which voice a visitor's screen "
                "reader uses."
            ),
            list_label="&Settings:",
            list_help="Each setting and its value now. Change sets the selected one.",
            rows=rows(),
            actions=[dlg.Action("&Change...", "Change the selected setting.", change)],
        )
        window.Destroy()

    def _choose_site_icon(
        self, profile: st.SiteProfile, api: Any, settings: dict[str, Any], save: Any
    ) -> None:
        def ask(images: list[wpm.MediaItem]) -> None:
            if not images:
                self.host.announce(
                    f"{profile.name}'s Media Library has no pictures. Upload a square one first."
                )
                return
            picked = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title="Site Icon",
                prompt="&Picture:",
                rows=[m.spoken() + ("" if m.width == m.height else ", not square") for m in images],
                help_text=(
                    "The small picture in a browser tab. It should be square and at least 512 "
                    "by 512."
                ),
            )
            if picked is None:
                return
            image = images[picked]
            if image.width != image.height:
                self.host.announce(
                    f"{image.title or image.filename} is {image.width} by {image.height}, not "
                    "square. Browsers would squash it; choose a square picture."
                )
                return
            save("site_icon", "Site icon", image.id, image.title or image.filename)

        self.background(  # type: ignore[attr-defined]
            "reading pictures",
            lambda: list(wpm.list_media(api, media_type="image")),
            ask,
        )

    # ------------------------------------------------------------------ #
    # Plugins (9.13)

    def cmd_plugins(self) -> None:
        if self.workbench_door("wordpress.plugins"):
            return  # the developer flag sends this door to the WordPress Workbench
        profile = self.admin_site("Plugins")
        if profile is None:
            return
        self.admin_load(
            profile,
            f"reading plugins on {profile.name}",
            "plugins",
            lambda api, _account: sa.list_plugins(api),
            lambda api, account, found: self._show_plugins(profile, api, account, found),
        )

    def _show_plugins(
        self, profile: st.SiteProfile, api: Any, account: wp.Account, plugins: list[sa.Plugin]
    ) -> None:
        live = list(plugins)

        def rows() -> list[str]:
            return [p.spoken() for p in live]

        def at(index: int | None) -> sa.Plugin | None:
            return live[index] if index is not None and index < len(live) else None

        def details(index: int) -> str:
            plugin = live[index]
            note = sa.accessibility_note(plugin)
            extra = f"\nAccessibility: {note}" if note else ""
            return f"{plugin.name}\n{plugin.description}{extra}"

        def toggle(index: int | None) -> object:
            plugin = at(index)
            if plugin is None:
                return None
            turning_on = not plugin.active
            verb = "Activate" if turning_on else "Deactivate"
            warning = (
                ""
                if turning_on
                else " Any blocks or shortcodes it provides stop working on the pages that use "
                "them."
            )
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title=f"{verb} Plugin",
                message=f"{verb} {plugin.name} on {profile.name}?{warning}",
                yes_label=f"{verb} {plugin.name}",
            ):
                return None

            def done(updated: sa.Plugin) -> None:
                if plugin in live:
                    live[live.index(plugin)] = updated
                state = "active" if updated.active else "inactive"
                self.host.announce(f"{updated.name} is now {state} on {profile.name}.")

            self.background(  # type: ignore[attr-defined]
                f"{verb.lower()}ing a plugin",
                lambda: sa.set_plugin_active(api, plugin, turning_on),
                done,
            )
            return None

        def add(_index: int | None) -> object:
            slug = dlg.ask_text(
                self.host.parent,
                self.host.show_modal,
                title="Add Plugin",
                prompt="&Plugin's WordPress.org name:",
                help_text=(
                    "The plugin's short name from its WordPress.org address: for "
                    "wordpress.org/plugins/wp-accessibility, type wp-accessibility. It is "
                    "installed inactive; activating it is a separate step."
                ),
            )
            if not slug or not slug.strip():
                return None
            slug = slug.strip().strip("/").rsplit("/", 1)[-1]
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Add Plugin",
                message=f"Install {slug} from WordPress.org on {profile.name}? It stays inactive.",
                yes_label="Install",
            ):
                return None

            def done(plugin: sa.Plugin) -> None:
                live.append(plugin)
                self.host.announce(
                    f"{plugin.name} installed on {profile.name}, inactive. Activate it when ready."
                )

            self.background("installing a plugin", lambda: sa.install_plugin(api, slug), done)  # type: ignore[attr-defined]
            return None

        def delete(index: int | None) -> object:
            plugin = at(index)
            if plugin is None:
                return None
            if plugin.active:
                self.host.announce(f"{plugin.name} is active. Deactivate it before deleting it.")
                return None
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Delete Plugin",
                message=f"Delete {plugin.name} and its files from {profile.name}?",
                yes_label=f"Delete {plugin.name}",
            ):
                return None
            self.site_job(
                "deleting a plugin",
                lambda: sa.delete_plugin(api, plugin),
                lambda _r: f"{plugin.name} deleted from {profile.name}.",
            )
            live.remove(plugin)
            return rows()

        def dashboard(_index: int | None) -> object:
            self.host.open_in_browser(profile.site_url.rstrip("/") + "/wp-admin/plugins.php")
            return None

        actions = [
            dlg.Action("&Activate or Deactivate...", "Turn the selected plugin on or off.", toggle)
        ]
        purpose = f"The plugins on {profile.name}."
        if sa.can(account, "install_plugins"):
            actions.append(
                dlg.Action(
                    "Add &Plugin...", "Install a plugin from WordPress.org.", add, needs_row=False
                )
            )
        else:
            purpose += " " + sa.cannot_sentence(profile.name, account, "install_plugins")
        if sa.can(account, "delete_plugins"):
            actions.append(dlg.Action("De&lete...", "Delete an inactive plugin.", delete))
        actions.append(
            dlg.Action(
                "Open in Das&hboard",
                "Open the site's Plugins screen in your browser, for updates.",
                dashboard,
                needs_row=False,
            )
        )
        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title=f"Plugins, {profile.name}",
            purpose=purpose,
            list_label="Pl&ugins:",
            list_help="Each plugin's name, version, whether it is active, and its author.",
            rows=rows(),
            details=details,
            actions=actions,
        )
        window.Destroy()

    # ------------------------------------------------------------------ #
    # Themes (9.13)

    def cmd_themes(self) -> None:
        if self.workbench_door("wordpress.themes"):
            return  # the developer flag sends this door to the WordPress Workbench
        profile = self.admin_site("Themes")
        if profile is None:
            return
        self.admin_load(
            profile,
            f"reading themes on {profile.name}",
            None,
            lambda api, account: sa.list_themes(api, active_only=not sa.can(account, "themes")),
            lambda api, account, found: self._show_themes(profile, account, found),
        )

    def _show_themes(
        self, profile: st.SiteProfile, account: wp.Account, themes: list[sa.Theme]
    ) -> None:
        def details(index: int) -> str:
            theme = themes[index]
            supports = ", ".join(theme.supports) or "nothing it declares"
            return (
                f"{theme.name}, version {theme.version}.\nThe theme supports: {supports}. This "
                "is why some options are offered in Block Settings and others are not."
            )

        def dashboard(_index: int | None) -> object:
            self.host.open_in_browser(profile.site_url.rstrip("/") + "/wp-admin/themes.php")
            return None

        purpose = (
            f"The themes on {profile.name}. WordPress does not let apps switch the theme, so "
            "Open in Dashboard takes you to the Themes screen for that."
        )
        if not sa.can(account, "themes"):
            purpose += " " + sa.cannot_sentence(profile.name, account, "themes")
        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title=f"Themes, {profile.name}",
            purpose=purpose,
            list_label="&Themes:",
            list_help="Each theme's name, version, and whether it is the active one.",
            rows=[t.spoken() for t in themes],
            details=details,
            actions=[
                dlg.Action(
                    "Open in Das&hboard",
                    "Open the site's Themes screen in your browser.",
                    dashboard,
                    needs_row=False,
                )
            ],
        )
        window.Destroy()


_SETTING_HELP = {
    "title": "The site's name, in every browser tab and search result.",
    "description": "A short line under the title saying what the site is for.",
    "language": (
        "The language code, for example en_GB or fr_FR. It is every page's language, so it "
        "decides the voice a visitor's screen reader uses."
    ),
    "timezone": "A city, for example Europe/London, so dates and schedules are right.",
    "date_format": "How dates look, in PHP's letters: F j, Y gives November 4, 2026.",
    "time_format": "How times look, in PHP's letters: g:i a gives 4:12 pm.",
    "email": "Where WordPress sends the site's notices. A change is confirmed by email first.",
    "posts_per_page": "How many posts a blog page shows.",
}
