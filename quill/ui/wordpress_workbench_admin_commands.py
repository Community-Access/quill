"""What REST cannot do, said and opened in wp-admin; and WordPress.org's directories (10B.3).

A mixin of :class:`quill.ui.wordpress_workbench_commands.WorkbenchRowCommands`:

- **Open in Dashboard** on a plugin, theme or Across Sites row says why the
  job is not on WordPress's REST API, then opens the exact wp-admin screen
  (:mod:`quill.core.wordpress.workbench_no_rest`). **Activate** on a theme
  does the same for Appearance > Themes.
- **Install on Sites Missing It** (Across Sites): a plugin is installed from
  WordPress.org through each site's own ``wp/v2/plugins`` after a preview; a
  theme cannot be, so each missing site's Add New screen opens instead.
- **Check on WordPress.org** and **Find a Plugin on WordPress.org** (WP-G): each
  plugin's directory facts and any closed or abandoned warning, added to the
  plugin rows for this window and to Install on Sites Missing It's preview;
  install from search through ``wp/v2/plugins``, inactive, after a preview
  that states the update and rollback limits.
- **Find a Theme on WordPress.org** and **Language Pack Status** ask
  ``api.wordpress.org`` (:mod:`quill.core.wordpress.dotorg`), only after a
  consent that names the host and exactly what is sent; the answer is kept
  for this window only.

Every request runs through ``self.background``.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Sequence
from datetime import date
from typing import Any

from quill.core.wordpress import dotorg
from quill.core.wordpress.workbench_no_rest import (
    ADMIN_SCREENS,
    PLUGIN_RECOVERY,
    admin_link,
    screen_for_row,
)
from quill.core.wordpress.workbench_rows import WbRow
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg

__all__ = ["WorkbenchAdminCommands"]

_UPDATE_LIMIT = ADMIN_SCREENS["plugin_auto_updates"].why
_MISSING = "Install on Sites Missing It"

_CONSENT = {
    "themes": (
        "Ask WordPress.org",
        "Search WordPress.org's theme directory? QUILL sends the words you type to "
        "api.wordpress.org, and nothing about your sites.",
    ),
    "plugins": (
        "Ask WordPress.org",
        "Ask WordPress.org's plugin directory? QUILL sends the words you type, or the short "
        "names (slugs) of the plugins in question, to api.wordpress.org. No site address, "
        "account or password is sent.",
    ),
    "updates": (
        "Ask WordPress.org",
        "Ask WordPress.org which versions are current? QUILL sends the short names (slugs) of "
        "this site's plugins and themes to api.wordpress.org, and asks for the current "
        "WordPress. No site address, installed version, account or password is sent.",
    ),
    "languages": (
        "Ask WordPress.org",
        "Ask WordPress.org which language packs it has? QUILL sends each WordPress version "
        "number your sites run to api.wordpress.org, and nothing else.",
    ),
}


def _row_plugin_slug(row: Any) -> str:
    """WordPress.org's short name for a plugin row, a site's or an Across Sites one."""
    if not isinstance(row, WbRow):
        return ""
    if row.kind == "plugin":
        return dotorg.plugin_slug(row.key)
    if row.kind == "across" and row.subkind == "plugins":
        for raw in (row.raw.get("objects") or {}).values():
            if isinstance(raw, dict) and raw.get("plugin"):
                return dotorg.plugin_slug(str(raw["plugin"]))
    return ""


class WorkbenchAdminCommands:
    """Open in Dashboard, theme Activate, Install on Sites Missing It, WordPress.org."""

    parent: Any
    commands: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    ensure: Callable[[Any], Any]
    show_modal: Callable[[Any, str], int]
    profile: Callable[[str], Any]
    refresh: Callable[[], None]

    # -- wp-admin -------------------------------------------------------------------

    def _site_url(self, site: str) -> str:
        profile = self.profile(site)
        return str(getattr(profile, "site_url", "") or "")

    def _open_screen(self, site: str, key: str, **query: str) -> None:
        screen = ADMIN_SCREENS[key]
        link = admin_link(self._site_url(site), key, **query)
        if not link:
            self.say(f"{site} has no address QUILL knows, so {screen.name} cannot be opened.")
            return
        self.say(f"{screen.why} Opening {screen.name} on {site} in your browser.")
        self.commands.host.open_in_browser(link)

    def _one_site(self, row: WbRow, title: str) -> str:
        """The site a row means: its own, or the one chosen from an Across Sites row."""
        if row.site:
            return row.site
        sites = sorted({s for group in (row.raw.get("variants") or {}).values() for s in group})
        if len(sites) <= 1:
            return sites[0] if sites else ""
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title=title,
            prompt="&Which site:",
            rows=sites,
            help_text="The site whose wp-admin screen opens in your browser.",
        )
        return "" if index is None else sites[index]

    def do_open_dashboard(self, _ref: Any, row: WbRow | None) -> None:
        if row is None:
            return
        key = screen_for_row(row.kind, row.subkind)
        if not key:
            self.say("Open in Dashboard works on a plugin, a theme, or Across Sites row.")
            return
        site = self._one_site(row, "Open in Dashboard")
        if site:
            self._open_screen(site, key)

    def do_activate_theme(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "theme":
            return
        if row.status == "active":
            self.say(f"{row.title} is already the theme on {row.site}.")
            return
        self._open_screen(row.site, "theme_activate", theme=row.key)

    # -- Across Sites: install where it is missing ----------------------------------

    def do_install_missing(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "across" or row.subkind not in ("plugins", "themes"):
            self.say("Install on Sites Missing It works on Across Sites > Plugins and Themes.")
            return
        missing: list[str] = list(row.raw.get("missing") or [])
        if not missing:
            self.say(f"Every site in scope already has {row.key}.")
            return
        objects: dict[str, Any] = row.raw.get("objects") or {}
        source = next(iter(objects.values()), {})
        holders = list(objects)
        # Only on the practice site: installing it on real sites carries practice work over.
        if (
            holders
            and all(self.is_practice(h) for h in holders)  # type: ignore[attr-defined]
            and not self.practice_crossing_ok(  # type: ignore[attr-defined]
                "Install on Sites Missing It", holders, missing
            )
        ):
            return
        if row.subkind == "themes":
            slug = str(source.get("stylesheet") or row.key)
            if not wdlg.ask_preview(
                self.parent,
                self.show_modal,
                title="Install on Sites Missing It",
                summary=(
                    f"WordPress's REST API cannot install a theme, so QUILL opens Appearance > "
                    f"Themes > Add New for {row.key} on {len(missing)} sites in your browser."
                ),
                lines=[f"{site}: opens Add New, searching for {slug}" for site in missing],
                yes="Open Them",
            ):
                return
            for site in missing:
                self._open_screen(site, "theme_install", search=slug)
            return
        slug = dotorg.plugin_slug(str(source.get("plugin") or ""))
        if not slug:
            self.say(f"{row.key} does not say its WordPress.org name, so it cannot be installed.")
            return
        if not self._dotorg_agreed("plugins"):
            self._install_preview(
                row.key, slug, missing, ["Not checked on WordPress.org."], _MISSING
            )
            return

        def checked(facts: dict[str, dotorg.DotorgPlugin | None]) -> None:
            self._remember_plugins(facts)
            self._install_preview(
                row.key, slug, missing, [self._plugin_words(row.key, slug)], _MISSING
            )

        self.background(
            "asking WordPress.org about a plugin", lambda: dotorg.plugin_details([slug]), checked
        )

    def _install_preview(
        self, name: str, slug: str, sites: Sequence[str], about: Sequence[str], title: str = ""
    ) -> None:
        """Preview installing *slug* on *sites*, inactive, with its limits; then install."""
        missing = list(sites)
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title=title or f"Install {name}",
            summary=(
                f"Each site installs {name} ({slug}) from WordPress.org, inactive. A plugin "
                "not in the WordPress.org directory fails on that site and the rest go on. "
                f"{_UPDATE_LIMIT} {PLUGIN_RECOVERY}"
            ),
            lines=[f"{site}: installs {slug}, left inactive" for site in missing]
            + [line for line in about if line],
            yes="Install",
        ):
            return

        def work() -> list[str]:
            failed: list[str] = []
            for site in missing:
                try:
                    self.ctx(site).api.post("wp/v2/plugins", {"slug": slug, "status": "inactive"})
                except Exception as exc:  # noqa: BLE001 - one site must not stop the rest
                    failed.append(f"{site}: {getattr(exc, 'plain', '') or exc}")
            return failed

        def done(failed: list[str]) -> None:
            made = len(missing) - len(failed)
            more = f" Not installed: {'; '.join(failed[:3])}" if failed else ""
            self.say(f"{name} installed on {made} of {len(missing)} sites, inactive.{more}")
            self.refresh()

        self.background("installing a plugin", work, done)

    # -- WordPress.org ----------------------------------------------------------------

    def _dotorg_agreed(self, what: str) -> bool:
        """Ask once per window before the first request to api.wordpress.org of *what*."""
        agreed: set[str] = self.__dict__.setdefault("_dotorg_consents", set())
        if what in agreed:
            return True
        title, message = _CONSENT[what]
        if not dlg.confirm(
            self.parent, self.show_modal, title=title, message=message, yes_label="Ask"
        ):
            self.say("Nothing was sent to WordPress.org.")
            return False
        agreed.add(what)
        return True

    def do_find_theme(self, _ref: Any, row: WbRow | None) -> None:
        words = dlg.ask_text(
            self.parent,
            self.show_modal,
            title="Find a Theme on WordPress.org",
            prompt="&Search for:",
            value=row.title if row is not None and row.kind in ("theme", "across") else "",
            help_text="Words in the theme's name or description. Only these words are sent.",
        )
        if not words or not words.strip() or not self._dotorg_agreed("themes"):
            return
        site = row.site if row is not None else ""
        missing = list(row.raw.get("missing") or []) if row is not None else []

        def found(themes: list[dotorg.DotorgTheme]) -> None:
            if not themes:
                self.say(f"WordPress.org has no theme matching {words.strip()}.")
                return
            index = dlg.ask_choice(
                self.parent,
                self.show_modal,
                title="Themes on WordPress.org",
                prompt="&Themes:",
                rows=[t.sentence for t in themes],
                help_text="Each theme in words. OK opens Add New for it on your site.",
            )
            if index is None:
                return
            chosen = themes[index]
            targets = [site] if site else missing
            if not targets:
                self.say(f"Choose a theme on a site, or an Across Sites row, to add {chosen.name}.")
                return
            for target in targets:
                self._open_screen(target, "theme_install", search=chosen.slug)

        self.background(
            "asking WordPress.org for themes", lambda: dotorg.search_themes(words), found
        )

    # -- WordPress.org's plugin directory (WP-G) ---------------------------------------

    def _known_plugins(self) -> dict[str, dotorg.DotorgPlugin | None]:
        found: dict[str, dotorg.DotorgPlugin | None] = self.__dict__.setdefault(
            "_dotorg_plugins", {}
        )
        return found

    def _remember_plugins(self, facts: dict[str, dotorg.DotorgPlugin | None]) -> None:
        self._known_plugins().update(facts)

    def _plugin_words(self, name: str, slug: str) -> str:
        known = self._known_plugins()
        if slug not in known:
            return ""
        plugin = known[slug]
        if plugin is None:
            return dotorg.not_listed_sentence(name)
        return plugin.sentence(date.today())

    def with_directory_facts(self, rows: Sequence[Any]) -> list[Any]:
        """Plugin rows, a site's or Across Sites', with what WordPress.org said, once asked."""
        if not self._known_plugins():
            return list(rows)
        told: list[Any] = []
        for row in rows:
            slug = _row_plugin_slug(row)
            if slug:
                words = self._plugin_words(row.title, slug)
                if words:
                    row = dataclasses.replace(row, detail=f"{row.detail} WordPress.org: {words}")
            told.append(row)
        return told

    def across_plugin_facts(self, rows: Sequence[Any]) -> list[Any]:
        """Off the UI thread: Across Sites plugin rows with WordPress.org's facts.

        The directory is asked only once the person has agreed to it in this
        window (the Plugin Directory command's question), and only for plugins
        it has not been asked about; until then the rows show what is known.
        """
        agreed: set[str] = self.__dict__.setdefault("_dotorg_consents", set())
        if "plugins" in agreed:
            known = self._known_plugins()
            wanted = [s for s in (_row_plugin_slug(r) for r in rows) if s and s not in known]
            if wanted:
                self._remember_plugins(dotorg.plugin_details(wanted))
        return self.with_directory_facts(rows)

    def do_plugin_directory(self, _ref: Any, row: WbRow | None) -> None:
        site = row.site if row is not None else ""
        if not site or not self._dotorg_agreed("plugins"):
            return

        def work() -> list[tuple[str, str]]:
            listed = self.ctx(site).api.get("wp/v2/plugins", context="edit")
            named = [
                (str(p.get("name") or p["plugin"]), dotorg.plugin_slug(str(p["plugin"])))
                for p in (listed if isinstance(listed, list) else [])
                if isinstance(p, dict) and p.get("plugin")
            ]
            self._remember_plugins(dotorg.plugin_details(slug for _n, slug in named))
            return named

        def done(named: list[tuple[str, str]]) -> None:
            lines = [f"{name}: {self._plugin_words(name, slug)}" for name, slug in named]
            dlg.show_report(
                self.parent,
                self.show_modal,
                title=f"Plugins on {site}, from WordPress.org",
                text="\n".join([*lines, "", _UPDATE_LIMIT, PLUGIN_RECOVERY]),
                help_text=(
                    "Each plugin on this site as WordPress.org's directory describes it, with "
                    "a warning for any it has closed or not seen updated in two years."
                ),
            )
            self.refresh()

        self.background("asking WordPress.org about plugins", work, done)

    def do_find_plugin(self, _ref: Any, row: WbRow | None) -> None:
        site = row.site if row is not None else ""
        if not site:
            self.say("Find a Plugin works on a site's Plugins list.")
            return
        words = dlg.ask_text(
            self.parent,
            self.show_modal,
            title="Find a Plugin on WordPress.org",
            prompt="&Search for:",
            value="",
            help_text="Words in the plugin's name or description. Only these words are sent.",
        )
        if not words or not words.strip() or not self._dotorg_agreed("plugins"):
            return

        def found(plugins: list[dotorg.DotorgPlugin]) -> None:
            if not plugins:
                self.say(f"WordPress.org has no plugin matching {words.strip()}.")
                return
            today = date.today()
            index = dlg.ask_choice(
                self.parent,
                self.show_modal,
                title="Plugins on WordPress.org",
                prompt="&Plugins:",
                rows=[p.sentence(today, describe=True) for p in plugins],
                help_text="Each plugin in words. OK previews installing it on this site.",
            )
            if index is None:
                return
            chosen = plugins[index]
            self._remember_plugins({chosen.slug: chosen})
            self._install_preview(chosen.name, chosen.slug, [site], [chosen.sentence(today)])

        self.background(
            "asking WordPress.org for plugins", lambda: dotorg.search_plugins(words), found
        )

    def do_language_packs(self, _ref: Any, row: WbRow | None) -> None:
        sites = list(getattr(self, "_profiles", {}))  # every site: which lack a pack
        if not sites or not self._dotorg_agreed("languages"):
            return

        def work() -> list[tuple[str, str]]:
            facts: list[tuple[str, str, str]] = []
            for site in sites:
                ctx = self.ensure(self.ctx(site))
                version = ctx.info.wp_version if ctx.info is not None else ""
                settings = ctx.api.get("wp/v2/settings")
                locale = str(settings.get("language", "") if isinstance(settings, dict) else "")
                facts.append((site, locale, version))
            return dotorg.site_languages(facts)

        def done(said: list[tuple[str, str]]) -> None:
            dlg.show_report(
                self.parent,
                self.show_modal,
                title="Language Pack Status",
                text="\n".join(sentence for _site, sentence in said),
                help_text=(
                    "Each site's language and whether WordPress.org has its pack. Installing "
                    "a pack is done in Dashboard > Updates or Settings > General."
                ),
            )

        self.background("asking WordPress.org about language packs", work, done)
