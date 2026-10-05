"""What the release-channel dialogs say (plan 7.2 to 7.6), kept out of wx.

Plain, warm and people-first: second person, short sentences, what could go
wrong said honestly, and how to come back said every time. The wording lives
here rather than in the dialogs so it can be read, reviewed and tested as text.

Titles are shared with each app's F1 catalogue (``surface_help``) through
:func:`window_titles`, so a window can never ship with a title its F1 help
does not know.

wx-free and strict-typed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from quill.core.updater.channels import BETA, DEV, channel_label
from quill.core.updater.runtime_slots import SLOT_EXTRA_MB
from quill.core.updater.switch import RiskContext

if TYPE_CHECKING:
    from quill.core.updater.going_back import ReturnAssessment

__all__ = [
    "CHOOSER_PURPOSE",
    "HISTORY_PURPOSE",
    "RISK_PURPOSE",
    "UNSIGNED_NOTE",
    "WAIT_PURPOSE",
    "WAIT_TITLE",
    "chooser_title",
    "history_title",
    "risk_confirm_label",
    "risk_text",
    "risk_title",
    "wait_text",
    "window_titles",
]

WAIT_TITLE = "Go back to Stable?"

#: F1 purposes, one per window, shared by every app's catalogue.
CHOOSER_PURPOSE = (
    "Choose which versions this app offers you: Stable, the one we recommend; "
    "Beta, new features a few weeks early; or Dev, work in progress for testers. "
    "Arrowing through the choices only explains them -- nothing changes until "
    "you choose Switch."
)
RISK_PURPOSE = (
    "Says plainly what could go wrong on Beta or Dev, how your settings are "
    "protected, and how to come back. Nothing changes unless you tick the box "
    "and choose Move."
)
WAIT_PURPOSE = (
    "Going back to Stable: straight away when Stable can read everything you "
    "have saved; otherwise by waiting for Stable to catch up, or by going back "
    "to the copy of your settings saved when you joined."
)
HISTORY_PURPOSE = (
    "A plain record of what the updater did for this app: checks, downloads, "
    "channel changes and the copies of your settings it saved. Read-only; "
    "nothing here changes anything."
)


def chooser_title(app_name: str) -> str:
    return f"Release Channel: {app_name}"


def history_title(app_name: str) -> str:
    return f"Update History: {app_name}"


def risk_title(app_name: str, channel: str) -> str:
    return f"Move {app_name} to {channel_label(channel)}?"


def window_titles(app_name: str) -> dict[str, str]:
    """Every channel window title *app_name* can show, with its F1 purpose."""
    return {
        chooser_title(app_name): CHOOSER_PURPOSE,
        history_title(app_name): HISTORY_PURPOSE,
        risk_title(app_name, BETA): RISK_PURPOSE,
        risk_title(app_name, DEV): RISK_PURPOSE,
        WAIT_TITLE: WAIT_PURPOSE,
        RETURN_SAFE_TITLE: RETURN_PURPOSE,
        RETURN_UNSAFE_TITLE: RETURN_PURPOSE,
    }


def _joined(names: tuple[str, ...]) -> str:
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def risk_confirm_label(channel: str) -> str:
    """The tick box the risk dialog needs before Move does anything."""
    if channel == DEV:
        return (
            "I &understand that Dev versions can break and that going back may lose recent changes."
        )
    return "I &understand that some things may not work right yet."


#: Beta and Dev builds are never code-signed (owner decision 2026-10-04), so
#: SmartScreen may stop their installer. One sentence, the same in both risk texts.
UNSIGNED_NOTE = (
    "- Beta and Dev versions aren't signed, so Windows may warn that the installer "
    "comes from an unknown publisher; that's expected, and you can choose More info, "
    "then Run anyway."
)


def risk_text(context: RiskContext) -> str:
    """The body of the risk dialog, as plain paragraphs and short lists."""
    name = context.display_name
    label = channel_label(context.target)
    moving = context.also_moving
    together = (
        f"\n\n{_joined(moving)} will move to {label} with {name}, and each gets its own saved copy."
        if moving
        else ""
    )
    protected = (
        "How you're protected\n"
        f"- Before switching, {name} saves a copy of {context.snapshot_covers}. "
        f"{context.snapshot_leaves}\n"
        "- You can come back to Stable any time from Help, Release Channel. "
        "If it's safe, you go straight back. If it isn't, you can keep the "
        "version you have until Stable catches up, or go back to the copy "
        "saved today.\n"
        "- If an update ever fails to start, it undoes itself and you are back "
        "on the version you had."
        + (
            f"\n- {label} versions of the QuillVille apps keep their own copy of the "
            f"engine they run on, so your Stable apps are never touched. That copy "
            f"uses about {SLOT_EXTRA_MB} MB more disk space until your last app comes "
            "back to Stable."
            if context.uses_shared_runtime
            else ""
        )
    )
    privacy = (
        f"Nothing about you is sent to us when you switch. The only thing {name} "
        "ever sends is a request for the list of versions."
    )
    if context.target == DEV:
        return (
            "Dev versions are built from work in progress, sometimes several times "
            "a week. They are meant for testing.\n\n"
            "What could happen\n"
            "- Expect things to break. Some days a Dev version may not start at all.\n"
            "- Dev versions are not checked with screen readers before they go out.\n"
            "- Dev versions may change how your data is saved more than once. Going "
            "back to Stable may mean using the copy saved today and losing changes "
            "you made since.\n"
            f"{UNSIGNED_NOTE}\n\n"
            f"{protected}\n\n"
            "If a developer didn't ask you to try Dev, Beta is probably the better "
            f"choice.{together}\n\n{privacy}"
        )
    return (
        f"{label} gets new features a few weeks before everyone else. In return, "
        "some things may not work right yet.\n\n"
        "What could happen\n"
        f"- Something might stop working, or {name} might close unexpectedly.\n"
        "- Your screen reader might miss something it should announce. We test "
        "every Stable version with JAWS and NVDA. Beta versions are tested less.\n"
        "- Your settings may be saved in a newer way that the Stable version "
        "can't read yet.\n"
        f"{UNSIGNED_NOTE}\n\n"
        f"{protected}{together}\n\n{privacy}"
    )


def wait_text(app_name: str, version: str, channel: str) -> str:
    """The body of the Go back to Stable? question (Phase 1: waiting only)."""
    label = channel_label(channel)
    return (
        f"You have {app_name} {version}, which is newer than Stable.\n\n"
        "Going straight back to an older version isn't offered yet, so the safe "
        f"way back is to wait: {app_name} keeps {version}, stops taking {label} "
        f"updates, and moves to Stable by itself when Stable reaches {version}. "
        "It will tell you when that happens.\n\n"
        "Nothing is installed and nothing of yours changes."
    )


# -- going back to Stable (plan 7.6, Phase 4) ---------------------------------------

RETURN_SAFE_TITLE = "Go back to Stable?"
RETURN_UNSAFE_TITLE = "Going straight back isn't safe yet"
RETURN_PURPOSE = (
    "How to come back to Stable from a newer version. When Stable can read "
    "everything you have saved, you can go back now. When it can't, you can "
    "wait for Stable to catch up, or go back to the copy saved when you joined. "
    "Close changes nothing."
)


def _version_words(version: str) -> str:
    from quill.core.versioning import ReleaseVersion

    parsed = ReleaseVersion.try_parse(version)
    return parsed.display() if parsed is not None else version


def return_text(assessment: ReturnAssessment, app_name: str, channel: str) -> str:
    """The body of the Go back to Stable? window, for the verdict it has."""
    from quill.core.updater.going_back import format_words

    stable = assessment.stable
    verdict = assessment.verdict
    if stable is None or verdict is None:
        return wait_text(app_name, _version_words(assessment.installed), channel)
    mine = _version_words(assessment.installed)
    target = _version_words(stable.version)
    label = channel_label(channel)
    waiting = (
        f"You can also stay on {mine} and move to Stable when it catches up. You won't "
        f"get more {label} updates while you wait."
    )
    if verdict.kind != "unsafe":
        text = (
            f"Stable is version {target}. You have {mine}.\n\n"
            f"Everything you have saved will work in {target}, so it's safe to go back "
            "now. Features that are only in "
            f"{label} will go away until they reach Stable."
        )
        if verdict.losses:
            text += (
                f"\n\n{target} doesn't know about some of the {format_words(verdict.losses)} "
                f"you changed in {label}. They'll go back to their usual values."
            )
        return text + "\n\n" + waiting
    what = format_words(verdict.blockers) or "what you have saved"
    if verdict.reason:
        why = f"Stable {target} can't be installed: {verdict.reason}."
    else:
        why = (
            f"{app_name} {mine} saved your {what} in a newer way that Stable {target} "
            f"can't read. If {target} were installed now, it might not see your {what}."
        )
    text = (
        f"{why}\n\nYou have safe choices:\n\n"
        f"Wait for Stable. Keep {mine}, stop taking {label} updates, and move to Stable "
        f"when it reaches {mine}. {app_name} will do this by itself and tell you."
    )
    if assessment.snapshot is not None:
        day = assessment.snapshot_date or "the day you joined"
        text += (
            f"\n\nUse the copy from {day}. Go back to how things were when you joined "
            f"{label}, then install {target}. Anything you added after {day} won't be in "
            "it. A copy of how things are right now is saved first, so nothing is thrown away."
        )
        if assessment.shared_kept:
            shared = ", ".join(assessment.shared_kept)
            text += (
                f" Your {shared} are shared with another app that is still on Beta or Dev, "
                "so they stay as they are."
            )
    else:
        text += (
            f"\n\nThere's no saved copy from before {label}, so the only safe choice is to wait."
        )
    return text
