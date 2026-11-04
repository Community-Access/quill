"""What the Forms site, export and AI commands share (wordpress.md 17a.7 to 17a.9, 17a.11).

A mixin, with no commands of its own, for
:class:`~quill.ui.forms_publish_commands.FormsPublishCommands`. It reaches the
editor only through ``self.host`` (the WordPress host both editors already
give the shared commands), and a site only through the shared WordPress
client: :func:`quill.core.wordpress.sites.api_for`, whose one door is
``send_to_site``. Forms adds no host and no way in.

Safe Mode turns off everything here that reaches a site or an AI (17a.11).
Writing, checking, Fill It In Yourself and the exports are local, and work.

The new-responses count (:func:`announce_new_responses_once`) is said once per
site per session, the first time a site is used -- by a WordPress command or
a Forms one -- the way the waiting-comments count is.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.forms import baf_site as bs
from quill.core.forms import published as pub
from quill.core.forms.menu import FORM_EXTENSION, is_form_path
from quill.core.wordpress import sites as st
from quill.ui import wordpress_dialogs as dlg

#: Sites already told their new-responses count this session.
_TOLD: set[str] = set()


def forget_told() -> None:
    """Start the once-a-session count afresh (tests, and a new session)."""
    _TOLD.clear()


def safe_mode_on(host: Any) -> bool:
    """Whether the editor runs in Safe Mode: its own flag, else the command line."""
    opener = getattr(host, "ai_editor", None)
    editor = opener() if callable(opener) else None
    flag = getattr(editor, "_safe_mode", None)
    if flag is not None:
        return bool(flag)
    from quill.stability.safe_mode import should_enable_safe_mode

    return should_enable_safe_mode(sys.argv, os.environ)


def announce_new_responses_once(
    host: Any, profile: st.SiteProfile, *, opener: Any = None, data_dir: Path | None = None
) -> None:
    """Say "Community Radio: 4 new responses to Event registration." once a session.

    Only when the site's setting allows it, only on a site with BITS
    Accessible Forms, and only when there are some. It reads the forms list --
    a count per form, never anybody's answers. A failure is silent: this is a
    courtesy, and the command the person asked for reports its own problems.
    """
    if not getattr(profile, "announce_new_responses", True) or profile.id in _TOLD:
        return
    _TOLD.add(profile.id)
    if safe_mode_on(host):
        return
    store = pub.PublishedStore(data_dir)

    def work() -> str:
        api = st.api_for(profile, opener=opener)
        if not bs.supports_baf(api):
            return ""
        counts = {f.id: (f.title, f.entry_count) for f in bs.list_forms(api)}
        return pub.waiting_sentence(profile.name, pub.new_responses(store, profile.id, counts))

    def done(sentence: str) -> None:
        if sentence:
            host.announce(sentence)

    host.run_task("Forms: counting new responses", work, done, lambda _exc: None)


def failure_sentence(exc: BaseException) -> str:
    from quill.ui.wordpress_commands import failure_sentence as wp_failure

    return wp_failure(exc)


def no_baf_sentence(command: str, site_name: str) -> str:
    return (
        f"{command} needs BITS Accessible Forms on {site_name}, and the site does not offer it. "
        "Install and activate the plugin there, then try again."
    )


class FormsSiteBase:
    # Provided by the commands class (FormsCommands, or a test's).
    host: Any

    # ------------------------------------------------------------------ #
    # local state

    def forms_data_dir(self) -> Path | None:
        return getattr(self, "_data_dir", None)

    def published(self) -> pub.PublishedStore:
        return pub.PublishedStore(self.forms_data_dir())

    def form_sites(self) -> st.SiteStore:
        return st.load_sites(self.forms_data_dir())

    # ------------------------------------------------------------------ #
    # gates

    def offline_only(self, command: str) -> bool:
        """True (and says why) in Safe Mode, where nothing reaches a site or an AI."""
        if not safe_mode_on(self.host):
            return False
        self.host.announce(
            f"{command} is off in Safe Mode, because it would reach your site or an AI. "
            "Writing, checking, Fill It In Yourself and saving in other formats still work."
        )
        return True

    def form_in_front(self, command: str) -> tuple[Path, Any] | None:
        """The form document in front, read; or say why there is none."""
        path = self.host.current_path()
        if not is_form_path(path):
            self.host.announce(
                f"{command} works in a form document, a {FORM_EXTENSION} file. Start one with "
                "New Form in the File menu, or open one."
            )
            return None
        from quill.ui import forms_doc as fd

        return Path(path), fd.read(self.host.current_text())

    def readable(self, command: str, doc: Any) -> bool:
        """The form reads cleanly and fits the model; says what to do when not."""
        from quill.core.forms import model as M

        problems = len(getattr(doc, "errors", []) or []) + len(M.validate(doc.model))
        if not problems:
            return True
        noun = "problem" if problems == 1 else "problems"
        self.host.announce(
            f"{command} stopped: this form has {problems} {noun} to fix first. Check This Form, "
            "in Tools, Forms, lists them with Go to It."
        )
        return False

    # ------------------------------------------------------------------ #
    # sites

    def choose_site(self, title: str, preferred_id: str = "") -> st.SiteProfile | None:
        store = self.form_sites()
        if not store.sites:
            self.host.announce(
                "Connect a WordPress site first, with Connect a Site in File, WordPress."
            )
            return None
        preferred = store.get(preferred_id)
        if preferred is not None:
            return preferred
        if len(store.sites) == 1:
            return store.sites[0]
        default = store.default
        index = dlg.ask_choice(
            self.host.parent,
            self.host.show_modal,
            title=title,
            prompt="&Site:",
            rows=[s.spoken() for s in store.sites],
            initial=store.sites.index(default) if default in store.sites else 0,
            help_text="Which of your WordPress sites has BITS Accessible Forms. Your default "
            "site is selected.",
        )
        return None if index is None else store.sites[index]

    def site_api(self, profile: st.SiteProfile) -> Any:
        """A signed client for *profile*; the first use in a session says the new count."""
        opener = getattr(self, "_opener", None)
        announce_new_responses_once(
            self.host, profile, opener=opener, data_dir=self.forms_data_dir()
        )
        return st.api_for(profile, opener=opener)

    def site_work(self, name: str, work: Callable[[], Any], done: Callable[[Any], None]) -> None:
        """Run *work* off the UI thread; a failure is one plain sentence."""
        self.host.run_task(
            f"Forms: {name}", work, done, lambda exc: self.host.announce(failure_sentence(exc))
        )

    def with_baf(
        self,
        command: str,
        profile: st.SiteProfile,
        name: str,
        work: Callable[[Any], Any],
        done: Callable[[Any], None],
    ) -> None:
        """*work(api)* only on a site whose REST index lists ``baf/v1``."""
        api = self.site_api(profile)
        missing = object()

        def guarded() -> Any:
            return work(api) if bs.supports_baf(api) else missing

        def finished(result: Any) -> None:
            if result is missing:
                self.host.announce(no_baf_sentence(command, profile.name))
                return
            done(result)

        self.site_work(name, guarded, finished)


__all__ = [
    "FormsSiteBase",
    "announce_new_responses_once",
    "failure_sentence",
    "forget_told",
    "no_baf_sentence",
    "safe_mode_on",
]
