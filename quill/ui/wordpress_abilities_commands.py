"""Abilities, opt-in one by one, and Ask the Site (wordpress.md 9.15, code.md decision 4).

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands`, offered
only when the site lists abilities (``wp-abilities/v1``, WordPress 6.9+).

* **Abilities** lists every ability by name. Each is off until checked here,
  kept per site on this computer.
* **Ask the Site** sends a question to the editor's chosen AI (Choose Your
  AI) with the abilities that are on. When the AI asks to run one, QUILL asks
  the person first, every time, naming the ability and exactly what it will
  be given; the answer then says what ran. Nothing runs without that yes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from quill.core.wordpress import abilities as ab
from quill.core.wordpress import site as wp
from quill.core.wordpress import site_features as sf
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_picture_ai as pai
from quill.ui.wordpress_api_site_base import WordPressApiSiteBase

if TYPE_CHECKING:
    from quill.core.wordpress import sites as st


def _why_not(site_name: str) -> Any:
    def check(index: sf.SiteIndex, _account: wp.Account) -> str:
        if index.supports(ab.NAMESPACE):
            return ""
        return (
            f"{site_name} offers no abilities for AI. That needs WordPress 6.9 or later, and a "
            "site or plugin that describes some."
        )

    return check


class WordPressAbilitiesCommands(WordPressApiSiteBase):
    def ability_choices(self, profile: st.SiteProfile) -> ab.AbilityChoices:
        return ab.AbilityChoices(self.local.root, profile.id)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------ #
    # Abilities: the list, each off until checked

    def cmd_abilities(self) -> None:
        if self.workbench_door("wordpress.abilities"):
            return  # the developer flag sends this door to the WordPress Workbench
        profile = self.chosen_site("Abilities")
        if profile is None:
            return
        self.when_offered(
            profile,
            f"reading {profile.name}'s abilities",
            _why_not(profile.name),
            lambda api, _index, _account: ab.list_abilities(api),
            lambda found: self._show_abilities(profile, found),
        )

    def _show_abilities(self, profile: st.SiteProfile, abilities: list[ab.Ability]) -> None:
        if not abilities:
            self.host.announce(f"{profile.name} lists no abilities.")
            return
        choices = self.ability_choices(profile)

        def rows() -> list[str]:
            on = choices.on()
            return [a.spoken(a.name in on) for a in abilities]

        def toggle(index: int | None) -> object:
            if index is None or index >= len(abilities):
                return None
            ability = abilities[index]
            turning_on = ability.name not in choices.on()
            if (
                turning_on
                and not ability.readonly
                and not dlg.confirm(
                    self.host.parent,
                    self.host.show_modal,
                    title="Turn On Ability",
                    message=(
                        f"Let Ask the Site offer {ability.label} on {profile.name}? It can change "
                        "the site. QUILL still asks you every time before it runs."
                    ),
                    yes_label=f"Turn On {ability.label}",
                )
            ):
                return None
            choices.set(ability.name, turning_on)
            self.host.announce(f"{ability.label} is {'on' if turning_on else 'off'}.")
            return rows()

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title=f"Abilities, {profile.name}",
            purpose=(
                f"The actions {profile.name} offers to AI. Each is off until you turn it on, "
                "and Ask the Site asks you before every use."
            ),
            list_label="&Abilities:",
            list_help="Each ability's name, whether it is on, and whether it can change the site.",
            rows=rows(),
            details=lambda index: abilities[index].details(),
            on_enter=toggle,
            actions=[
                dlg.Action("&Turn On or Off", "Turn the selected ability on or off.", toggle),
            ],
        )
        window.Destroy()

    # ------------------------------------------------------------------ #
    # Ask the Site

    def cmd_ask_site(self) -> None:
        profile = self.chosen_site("Ask the Site")
        if profile is None:
            return
        self.when_offered(
            profile,
            f"reading {profile.name}'s abilities",
            _why_not(profile.name),
            lambda api, _index, _account: ab.list_abilities(api),
            lambda found: self._ask_site(profile, found),
        )

    def _ask_site(self, profile: st.SiteProfile, abilities: list[ab.Ability]) -> None:
        on = self.ability_choices(profile).on()
        enabled = [a for a in abilities if a.name in on]
        if not enabled:
            self.host.announce(
                f"No ability of {profile.name} is turned on. Turn them on one by one in "
                "Abilities, then ask again."
            )
            return
        ai = pai.editor_of(self.host)
        if not pai.switched_on(ai, self.host.announce):
            return
        question = dlg.ask_text(
            self.host.parent,
            self.host.show_modal,
            title=f"Ask the Site, {profile.name}",
            prompt="&Question:",
            multiline=True,
            help_text=(
                "Ask about your site. The AI you chose in Choose Your AI may ask to use one of "
                "the abilities you turned on; QUILL asks you before it runs."
            ),
        )
        if question is None or not question.strip():
            return

        def planned(answer: str) -> None:
            plan = ab.parse_plan(answer, enabled)
            if plan is None:
                self._show_answer(profile, ab.answer_with_uses(answer, profile.name, []))
                return
            ability, given = plan
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Run Ability",
                message=ab.approval_message(profile.name, ability, given),
                yes_label=f"Run {ability.label}",
            ):
                self.host.announce(f"Nothing was run on {profile.name}.")
                return
            api = self.api(profile)  # type: ignore[attr-defined]

            def ran(result: Any) -> None:
                prompt = ab.answer_prompt(profile.name, question, ability, given, result)
                pai.ask_text(
                    ai,
                    prompt,
                    lambda final: self._show_answer(
                        profile, ab.answer_with_uses(final, profile.name, [(ability, given)])
                    ),
                    self.host.announce,
                )

            self.background(  # type: ignore[attr-defined]
                f"running {ability.label} on {profile.name}",
                lambda: ab.run_ability(api, ability, given),
                ran,
            )

        pai.ask_text(
            ai, ab.plan_prompt(profile.name, question, enabled), planned, self.host.announce
        )

    def _show_answer(self, profile: st.SiteProfile, text: str) -> None:
        dlg.show_report(
            self.host.parent,
            self.host.show_modal,
            title=f"Ask the Site, {profile.name}",
            text=text,
            help_text="The AI's answer, then which of the site's abilities ran to get it.",
        )
