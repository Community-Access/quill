"""Fonts and Synced Patterns (wordpress.md 9.13).

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands`, gathered
by :class:`~quill.ui.wordpress_admin_commands.WordPressAdminCommands`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from quill.core.wordpress import site as wp
from quill.core.wordpress import site_library as lib
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.pattern_directory import load_categories as pattern_categories
from quill.ui import wordpress_dialogs as dlg
from quill.ui.wordpress_admin_base import WordPressAdminBase

if TYPE_CHECKING:
    from quill.core.wordpress import sites as st


class WordPressDesignCommands(WordPressAdminBase):
    # ------------------------------------------------------------------ #
    # Fonts (6.5+)

    def cmd_fonts(self) -> None:
        if self.workbench_door("wordpress.fonts"):
            return  # the developer flag sends this door to the WordPress Workbench
        profile = self.admin_site("Fonts")
        if profile is None:
            return

        def work(api: Any, _account: wp.Account) -> list[lib.Font] | None:
            try:
                return lib.list_fonts(api)
            except WordPressApiError as exc:
                if exc.status == 404:
                    return None
                raise

        def show(api: Any, _account: wp.Account, fonts: list[lib.Font] | None) -> None:
            if fonts is None:
                self.host.announce(
                    f"{profile.name} has no font library. It needs WordPress 6.5 or newer and a "
                    "block theme."
                )
                return
            self._show_fonts(profile, api, fonts)

        self.admin_load(profile, f"reading fonts on {profile.name}", "fonts", work, show)

    def _show_fonts(self, profile: st.SiteProfile, api: Any, fonts: list[lib.Font]) -> None:
        live = list(fonts)

        def rows() -> list[str]:
            return [f.spoken() for f in live]

        def install(_index: int | None) -> object:
            def ask(choices: list[lib.FontChoice]) -> None:
                if not choices:
                    self.host.announce(f"{profile.name} offers no font collections.")
                    return
                picked = dlg.ask_choice(
                    self.host.parent,
                    self.host.show_modal,
                    title="Install Font",
                    prompt="&Font:",
                    rows=[c.spoken() for c in choices],
                    help_text="Fonts from the site's collections, each with its style in words.",
                )
                if picked is None:
                    return
                choice = choices[picked]
                if not dlg.confirm(
                    self.host.parent,
                    self.host.show_modal,
                    title="Install Font",
                    message=f"Install {choice.name} on {profile.name}?",
                    yes_label=f"Install {choice.name}",
                ):
                    return

                def done(font: lib.Font) -> None:
                    live.append(font)
                    self.host.announce(f"{font.name} installed on {profile.name}.")

                self.background(  # type: ignore[attr-defined]
                    "installing a font", lambda: lib.install_font(api, choice), done
                )

            self.background(  # type: ignore[attr-defined]
                "reading font collections", lambda: lib.list_font_choices(api), ask
            )
            return None

        def delete(index: int | None) -> object:
            if index is None or index >= len(live):
                return None
            font = live[index]
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Delete Font",
                message=(
                    f"Delete {font.name} from {profile.name}? Text set in it falls back to "
                    "the theme's own font."
                ),
                yes_label=f"Delete {font.name}",
            ):
                return None
            self.site_job(
                "deleting a font",
                lambda: lib.delete_font(api, font.id),
                lambda _r: f"{font.name} deleted from {profile.name}.",
            )
            live.remove(font)
            return rows()

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title=f"Fonts, {profile.name}",
            purpose=(
                f"The fonts installed on {profile.name}, each described in words. Which font "
                "the theme uses is chosen in the site editor."
            ),
            list_label="&Fonts:",
            list_help="Each font's name, its style and what it suits, and how many faces it has.",
            rows=rows(),
            actions=[
                dlg.Action(
                    "&Install...",
                    "Install a font from the site's collections.",
                    install,
                    needs_row=False,
                ),
                dlg.Action("&Delete...", "Delete the selected font.", delete),
            ],
        )
        window.Destroy()

    # ------------------------------------------------------------------ #
    # Synced Patterns

    def cmd_synced_patterns(self) -> None:
        if self.workbench_door("wordpress.synced_patterns"):
            return  # the developer flag sends this door to the WordPress Workbench
        profile = self.admin_site("Synced Patterns")
        if profile is None:
            return
        self.admin_load(
            profile,
            f"reading patterns on {profile.name}",
            "patterns",
            lambda api, _account: (
                lib.list_patterns(api),
                lib.pattern_uses(api),
                pattern_categories(api),
            ),
            # Grouped by pattern category first when the site has them (9.15).
            lambda api, _account, data: self._patterns_shown(profile, api, *data),
        )

    def _patterns_shown(self, profile: Any, api: Any, patterns: Any, uses: Any, cats: Any) -> None:
        by_category = getattr(self, "patterns_by_category", None)
        if by_category is not None:
            by_category(profile, api, patterns, uses, cats)
        else:
            self._show_patterns(profile, api, patterns, uses)

    def _show_patterns(
        self,
        profile: st.SiteProfile,
        api: Any,
        patterns: list[lib.Pattern],
        uses: dict[int, list[lib.Use]],
    ) -> None:
        live = list(patterns)

        def rows() -> list[str]:
            return [p.spoken(len(uses.get(p.id, []))) for p in live]

        def at(index: int | None) -> lib.Pattern | None:
            return live[index] if index is not None and index < len(live) else None

        def details(index: int) -> str:
            found = uses.get(live[index].id, [])
            if not found:
                return "Not used on any page or post."
            return "Used in:\n" + "\n".join(f"{u.title} ({u.kind})" for u in found)

        def edit(index: int | None) -> object:
            pattern = at(index)
            if pattern is None:
                return None
            text = dlg.ask_text(
                self.host.parent,
                self.host.show_modal,
                title=f"Edit {pattern.title}",
                prompt="&Blocks:",
                value=pattern.content,
                multiline=True,
                help_text="The pattern's blocks as the site keeps them. Keep the block comments.",
            )
            if text is None or text == pattern.content:
                return None
            count = len(uses.get(pattern.id, []))
            if (
                pattern.synced
                and count
                and not dlg.confirm(
                    self.host.parent,
                    self.host.show_modal,
                    title="Save Synced Pattern",
                    message=(
                        f"Saving {pattern.title} changes it on all {count} pages and posts that "
                        f"use it on {profile.name}. Save?"
                    ),
                    yes_label="Save Everywhere",
                )
            ):
                return None
            self.site_job(
                "saving a pattern",
                lambda: lib.save_pattern_content(api, pattern.id, text),
                lambda _r: f"{pattern.title} saved on {profile.name}.",
            )
            live[live.index(pattern)] = lib.Pattern(pattern.id, pattern.title, pattern.synced, text)
            return None

        def rename(index: int | None) -> object:
            pattern = at(index)
            if pattern is None:
                return None
            name = dlg.ask_text(
                self.host.parent,
                self.host.show_modal,
                title="Rename Pattern",
                prompt="&Name:",
                value=pattern.title,
                help_text="The pattern's name in the inserter.",
            )
            if not name or not name.strip() or name.strip() == pattern.title:
                return None
            new = name.strip()
            self.site_job(
                "renaming a pattern",
                lambda: lib.rename_pattern(api, pattern.id, new),
                lambda _r: f"Pattern renamed to {new}.",
            )
            live[live.index(pattern)] = lib.Pattern(
                pattern.id, new, pattern.synced, pattern.content
            )
            return rows()

        def unsync(index: int | None) -> object:
            pattern = at(index)
            if pattern is None:
                return None
            if not pattern.synced:
                self.host.announce(f"{pattern.title} is already not synced.")
                return None
            found = uses.get(pattern.id, [])
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Unsync Pattern",
                message=(
                    f"Turn each of the {len(found)} uses of {pattern.title} on {profile.name} "
                    "into ordinary blocks, then stop syncing it? Every page keeps what it shows."
                ),
                yes_label="Unsync",
            ):
                return None
            self.site_job(
                "unsyncing a pattern",
                lambda: lib.unsync_pattern(api, pattern, found),
                lambda n: (
                    f"{pattern.title} is no longer synced; {n} pages now hold their own copy."
                ),
            )
            live[live.index(pattern)] = lib.Pattern(
                pattern.id, pattern.title, False, pattern.content
            )
            uses.pop(pattern.id, None)
            return rows()

        def delete(index: int | None) -> object:
            pattern = at(index)
            if pattern is None:
                return None
            count = len(uses.get(pattern.id, []))
            if count:
                self.host.announce(
                    f"{pattern.title} is used in {count} places, which would show an error. "
                    "Unsync it first, then delete it."
                )
                return None
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Delete Pattern",
                message=f"Delete the pattern {pattern.title} from {profile.name}?",
                yes_label=f"Delete {pattern.title}",
            ):
                return None
            self.site_job(
                "deleting a pattern",
                lambda: lib.delete_pattern(api, pattern.id),
                lambda _r: f"{pattern.title} deleted from {profile.name}.",
            )
            live.remove(pattern)
            return rows()

        def from_selection(_index: int | None) -> object:
            selected = self.host.selected_text()
            if not selected.strip():
                self.host.announce("Select the blocks for the pattern in the editor first.")
                return None
            name = dlg.ask_text(
                self.host.parent,
                self.host.show_modal,
                title="New Pattern from Selection",
                prompt="&Name:",
                help_text="The new synced pattern's name in the inserter.",
            )
            if not name or not name.strip():
                return None
            content = self._selection_as_blocks(selected)

            def done(pattern: lib.Pattern) -> None:
                live.append(pattern)
                self.host.announce(f"Synced pattern {pattern.title} made on {profile.name}.")

            self.background(  # type: ignore[attr-defined]
                "making a pattern", lambda: lib.create_pattern(api, name.strip(), content), done
            )
            return None

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title=f"Synced Patterns, {profile.name}",
            purpose=(
                f"The reusable patterns on {profile.name}. A synced pattern is the same "
                "everywhere it is used, so changing it changes every page that uses it."
            ),
            list_label="&Patterns:",
            list_help="Each pattern's name, whether it is synced, and how many places use it.",
            rows=rows(),
            details=details,
            actions=[
                dlg.Action("&Edit...", "Change the selected pattern's blocks.", edit),
                dlg.Action("&Rename...", "Rename the selected pattern.", rename),
                dlg.Action("&Unsync...", "Make each use ordinary blocks.", unsync),
                dlg.Action("De&lete...", "Delete an unused pattern.", delete),
                dlg.Action(
                    "&New from Selection...",
                    "Make a synced pattern from the blocks selected in the editor.",
                    from_selection,
                    needs_row=False,
                ),
            ],
        )
        window.Destroy()

    def _selection_as_blocks(self, selected: str) -> str:
        copy = self.local.copy_for_path(self.host.current_path())  # type: ignore[attr-defined]
        if copy is None or copy.text_format == "html" or "<!-- wp:" in selected:
            return selected
        from quill.core.wordpress import fences

        islands = copy.properties.get("islands") or {}
        return fences.convert_markdown(selected, islands).html
