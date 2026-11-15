"""Watches on the editor's existing WordPress timer (PRD 15.7, W7).

The two-minute timer that already autosaves and retries the offline queue
(:mod:`quill.ui.wordpress_offline_commands`) calls :func:`watch_round` on
every tick. It does nothing until Watches are due (at most every fifteen
minutes, :func:`quill.core.wordpress.workbench_watches.due`) and are turned
on in Workbench Options; then one round runs off the UI thread over every
connected site, and each sentence it finds is announced through the editor's
own announce, which speaks and brailles. Counts and changes are always
spoken: the shared feedback rule (``quill/core/action_feedback.py``) keeps
anything that carries a number out of the sound-or-speech choice.

Shared by QUILL and QUILL Lite through ``WordPressCommands``.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from quill.core.wordpress.workbench_editorial import load_reviews, save_reviews
from quill.core.wordpress.workbench_options import load_options
from quill.core.wordpress.workbench_watches import check, due, load_state, save_state

__all__ = ["watch_round"]

_log = logging.getLogger(__name__)


def watch_round(commands: Any) -> None:
    """One Watches round if one is due; quiet when nothing changed or nothing is on.

    The round is claimed (its time saved) before any site is asked, so QUILL
    and QUILL Lite open side by side do not both run it and say it twice.
    """
    base = getattr(commands, "_data_dir", None)
    options = load_options(base)
    if not options.watches or getattr(commands, "_watching", False):
        return
    state = load_state(base)
    if not due(state, options.watch_minutes):
        return
    store = commands.sites()
    if not store.sites:
        return
    commands._watching = True
    state.last_round = time.time()
    save_state(state, base)
    reviews = load_reviews(base) if "review" in options.watches else []

    def work() -> list[str]:
        targets = []
        unreachable: list[str] = []
        for profile in store.sites:
            name = profile.name or profile.host
            try:
                api = commands.api(profile)
                info = api.get("")
                spaces = info.get("namespaces", []) if isinstance(info, dict) else []
                targets.append((name, api, [str(n) for n in spaces]))
            except Exception:  # noqa: BLE001 - a site that does not answer waits for next round
                _log.info("Watches: %s did not answer", profile.host)
                unreachable.append(name)
        said = check(targets, state, options.watches, unreachable=unreachable, reviews=reviews)
        save_state(state, base)
        if reviews:
            waiting = [
                r
                for r in reviews
                if state.reviews.get(f"{r.site}:{r.item_id}") in (None, "pending")
            ]
            if len(waiting) != len(reviews):
                save_reviews(waiting, base)
        return said

    def done(said: list[str]) -> None:
        commands._watching = False
        for sentence in said:
            commands.host.announce(sentence)

    def failed(_error: BaseException) -> None:
        commands._watching = False

    commands.host.run_task("WordPress: Watches", work, done, failed)
