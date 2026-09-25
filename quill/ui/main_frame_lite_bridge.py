"""Make QUILL the shape of the editor somebody already knows (bad.md P2.4).

Two things, and they belong together because they are the same offer seen from
two sides. A **profile** can promise a setting -- the QUILL Lite profile makes a
plain text document on Ctrl+N, because a profile named after a product that made
the wrong kind of document would keep the letter of its name and break its
promise, with the user finding out one document later at the Save As dialog.
And **bringing a QUILL Lite setup over** is the other half: the menus can be made
to match in one press, and the abbreviations, dictionary and rebound keys behind
them are months of work that should not have to be retyped.

The rule the whole thing turns on is that nothing here happens quietly.
``quill/core/lite/paths.py`` explains why QUILL Lite keeps its own folder: a
product that silently adopts another's settings is deciding something nobody
asked it to. So the offer is made once, in a question that says what it would
do -- with counts, because a count is the one thing a listener cannot get by
exploring a dialog -- and declining costs nothing.

The reading, translating and merging are all in the wx-free
:mod:`quill.core.lite_bridge`; this module is the question and the answer.

Extracted from ``main_frame.py`` on 2026-09-18 under GATE-11.
"""

from __future__ import annotations

__all__ = ["LiteBridgeMixin"]


class LiteBridgeMixin:
    """Profile-promised settings, and bringing a QUILL Lite setup across."""

    def apply_profile_settings(self, profile_id: str) -> str:
        """Apply the settings a profile's own NAME promises. Returns what it said.

        A profile that renames the menus and leaves the document model alone is
        a profile that half keeps its word (bad.md P2.4). QUILL Lite's profiles
        have carried this since they shipped -- its Notepad profile makes a
        plain document and its WordPad profile a rich one -- and QUILL's
        QUILL Lite profile has to do the same or the name is decoration.

        Empty string when the profile promises nothing, which is every profile
        that is a statement about which menus exist.
        """
        from quill.core.features import PROFILE_DEFINITIONS
        from quill.core.settings import save_settings

        profile = PROFILE_DEFINITIONS.get(profile_id)
        promised = tuple(getattr(profile, "settings", ()) or ())
        if not promised:
            return ""
        changed: list[str] = []
        for field_name, value in promised:
            if not hasattr(self.settings, field_name):
                continue
            if getattr(self.settings, field_name) == value:
                continue
            setattr(self.settings, field_name, value)
            changed.append(field_name.replace("_", " "))
        if not changed:
            return ""
        save_settings(self.settings)
        return "Also set " + ", ".join(changed) + "."

    def offer_bring_from_quilllite(self, profile_id: str) -> bool:
        """On activating the QUILL Lite profile, offer to bring a QUILL Lite setup over.

        Offered, not done. The person has just said "make QUILL look like the
        editor I know", which is exactly the moment the question is worth asking
        and exactly the wrong moment to answer it for them: their QUILL Lite
        abbreviations and dictionary are months of work, and adopting them
        silently is the behaviour ``quill/core/lite/paths.py`` refuses on
        principle. ``True`` when something was brought.

        Once only: a profile switched back and forth should not keep asking.
        """
        from quill.core.features import PROFILE_QUILLLITE

        if profile_id != PROFILE_QUILLLITE:
            return False
        if getattr(self.settings, "quilllite_bring_offered", False):
            return False
        self.settings.quilllite_bring_offered = True
        return self.bring_from_quilllite(asked_for_it=False)

    def bring_from_quilllite(self, *, asked_for_it: bool = True) -> bool:
        """Show what a QUILL Lite setup would bring over, and bring it if asked.

        The plan is read and *described* before anything is applied, because "it
        copied your settings" is not something a listener can verify afterwards
        by looking at the screen. The description says what is copied, what
        becomes shared, and what is being left behind -- the last of those
        because an import that says nothing about its own limits reads as having
        brought everything.
        """
        from quill.core.lite_bridge import describe_plan, plan_bring_from_lite
        from quill.core.settings import save_settings

        plan = plan_bring_from_lite()
        summary = describe_plan(plan)
        if plan.lite_dir is None or plan.is_empty:
            if asked_for_it:
                self._show_message_box(summary, "Bring my QUILL Lite settings", self._wx.OK)
            else:
                self._set_status(summary)
            return False

        wx = self._wx
        answer = self._show_message_box(
            f"QUILL can start from your QUILL Lite setup:\n\n{summary}\n\nBring it over?",
            "Bring my QUILL Lite settings",
            wx.YES_NO | wx.ICON_QUESTION,
        )
        if answer != wx.YES:
            self._set_status("Left QUILL's own settings as they are.")
            return False

        from quill.core.lite_bridge import apply_bring_plan, enable_lite_sharing
        from quill.core.paths import app_data_dir

        for field_name, value in plan.settings.items():
            if hasattr(self.settings, field_name):
                setattr(self.settings, field_name, value)
        save_settings(self.settings)
        if plan.keymap:
            self._merge_keymap_overrides(plan.keymap)
        added = apply_bring_plan(plan, app_data_dir())
        switches = enable_lite_sharing(plan)
        entries = sum(added.values())
        self._announce(
            f"Brought {len(plan.settings)} setting(s) and {len(plan.keymap)} key(s) from "
            f"QUILL Lite, and added {entries} entr{'y' if entries == 1 else 'ies'} to "
            f"{len(added)} store(s). "
            + (
                f"QUILL Lite now reads {len(switches)} of them from QUILL, so a change in "
                "either is a change in both. "
                if switches
                else ""
            )
            + "Restart QUILL to see every change."
        )
        return True

    def _merge_keymap_overrides(self, bindings: dict[str, str]) -> None:
        """Save *bindings* into the user's keymap, keeping what they already set.

        Their own existing override wins: somebody who has already rebound a
        chord in QUILL has said something more recent than what QUILL Lite's file
        remembers, and an import that overwrites it is an import that undoes
        their work.
        """
        from quill.core.keymap import load_keymap, save_keymap

        current = dict(load_keymap())
        for command_id, chord in bindings.items():
            current.setdefault(command_id, chord)
        save_keymap(current)
