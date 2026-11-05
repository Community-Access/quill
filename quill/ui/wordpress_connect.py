"""Connecting a site: three fields, or one press with the browser (wordpress.md 4.1 to 4.3).

The flow, for a self-hosted site:

1. The person types the address (and, for the manual route, the username and
   an application password) and presses Connect. QUILL verifies before it
   saves: it reads the account (``users/me``) and the site's own name, so a
   wrong password is caught here, in words, not at the first Publish.
2. Or they press Get Password with My Browser. QUILL reads the site's REST
   index for the Authorize Application address and the WordPress version.
   * On a site with the loopback change (r62096) it listens once on
     ``127.0.0.1`` and WordPress hands the password straight back (tier 1).
   * On an older site WordPress shows the password with a Copy button, and
     QUILL waits on one Paste field, offering a password-shaped clipboard
     value when focus comes back (tier 2).
   * If the site has application passwords turned off, it says so (tier 3).

WordPress.com needs QUILL's registered WordPress.com app (wordpress.md 4.3).
Until that client id exists the flow says so plainly and points at the
application-password route, which WordPress.com sites on plugin plans accept.
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from typing import TYPE_CHECKING, Any

from quill.core.wordpress import signin
from quill.core.wordpress import site as wp
from quill.core.wordpress import sites as st
from quill.core.wordpress.api import SiteAddress, SiteAuth, WordPressApi
from quill.ui import wordpress_dialogs as dlg

if TYPE_CHECKING:
    from quill.ui.wordpress_commands import WordPressCommands

#: A stable id for QUILL in WordPress's application-password list, so a second
#: connection from the same computer is recognisable as QUILL's.
QUILL_APP_ID = "5b2f8a1e-7c34-4d9a-9a6e-3e0f2c1b7d55"
QUILL_APP_NAME = "QUILL"

#: Filled in once QUILL's WordPress.com app is registered (wordpress.md 4.3).
WPCOM_CLIENT_ID = ""


class ConnectFlow:
    def __init__(self, commands: WordPressCommands) -> None:
        self.c = commands

    @property
    def host(self) -> Any:
        return self.c.host

    def start(
        self, *, site_url: str = "", error: str = "", answer: dlg.ConnectAnswer | None = None
    ) -> dlg.ConnectAnswer | None:
        if answer is None and site_url:
            answer = dlg.ConnectAnswer(kind="self_hosted", site_url=site_url, username="")
        chosen = dlg.ask_connect(self.host.parent, self.host.show_modal, answer=answer, error=error)
        if chosen is None:
            return None
        chosen.site_url = normalise_address(chosen.site_url)
        if chosen.kind == "wpcom":
            self.host.announce(wpcom_unavailable_sentence())
            return chosen
        if chosen.use_browser:
            self._browser(chosen)
        else:
            self._verify_and_save(chosen)
        return chosen

    # -- the manual route --------------------------------------------------

    def _verify_and_save(self, answer: dlg.ConnectAnswer) -> None:
        if not answer.username or not answer.password:
            self.start(
                error=(
                    "Enter the username and the application password, or press Get Password with "
                    "My Browser."
                ),
                answer=answer,
            )
            return
        api = WordPressApi(
            SiteAddress(answer.site_url),
            SiteAuth("app_password", answer.username, answer.password),
            opener=self.c._opener,
        )

        def check() -> tuple[wp.Account, wp.SiteInfo]:
            return wp.load_account(api), wp.load_site_info(api)

        def done(result: tuple[wp.Account, wp.SiteInfo]) -> None:
            account, info = result
            store = self.c.sites()
            existing = next(
                (
                    s
                    for s in store.sites
                    if s.site_url == answer.site_url and s.username == answer.username
                ),
                None,
            )
            profile = st.SiteProfile(
                id=existing.id if existing else st.new_site_id(),
                name=answer.name or info.name or (existing.name if existing else answer.site_url),
                site_url=answer.site_url,
                username=answer.username,
                role=account.role_name,
                wp_version=info.wp_version,
            )
            st.save_secret(profile.id, answer.password)
            store.upsert(profile)
            self.c.save_sites(store)
            self.host.announce(f"Connected to {profile.name} as {account.role_name}.")

        def failed(exc: BaseException) -> None:
            from quill.ui.wordpress_commands import failure_sentence

            self.start(error=failure_sentence(exc), answer=answer)

        self.host.run_task("WordPress: connecting", check, done, failed)

    def verify(self, profile: st.SiteProfile) -> None:
        api = self.c.api(profile)

        def done(account: wp.Account) -> None:
            store = self.c.sites()
            store.upsert(replace(profile, role=account.role_name))
            self.c.save_sites(store)
            self.host.announce(f"{profile.name} accepts QUILL. You are {account.role_name} there.")

        self.c.background(f"checking {profile.name}", lambda: wp.load_account(api), done)

    # -- the browser route (4.2) --------------------------------------------

    def _browser(self, answer: dlg.ConnectAnswer) -> None:
        index_api = WordPressApi(
            SiteAddress(answer.site_url), SiteAuth("none"), opener=self.c._opener
        )
        self.c.background(
            "reading the site",
            lambda: wp.load_site_info(index_api),
            lambda info: self._authorize(answer, info),
        )

    def _authorize(self, answer: dlg.ConnectAnswer, info: wp.SiteInfo) -> None:
        if not info.authorize_url:
            self.start(
                error=(
                    "This site has application passwords turned off, so QUILL cannot ask for one."
                    " Ask the "
                    "site's administrator to turn them on, or make one in your WordPress profile "
                    "if you can."
                ),
                answer=answer,
            )
            return
        state = signin.new_state()
        if signin.supports_loopback_success_url(info.wp_version):
            listener = signin.LoopbackListener(timeout=300.0)
            redirect = listener.start()
            url = signin.build_authorize_application_url(
                info.authorize_url,
                app_name=QUILL_APP_NAME,
                app_id=QUILL_APP_ID,
                success_url=redirect,
                reject_url=redirect,
                state=state,
            )
            self.host.open_in_browser(url)
            self.host.announce(
                f"Approve QUILL in your browser. QUILL is waiting for {info.name or 'the site'}."
            )

            def done(received: str | None) -> None:
                if received is None:
                    self.host.announce(
                        "QUILL stopped waiting for the browser. Try again when you are ready."
                    )
                    return
                result = signin.parse_authorize_application_redirect(received, state)
                if isinstance(result, signin.Rejected):
                    self.host.announce("You chose not to connect QUILL. Nothing was saved.")
                    return
                answer.username = result.user_login
                answer.password = result.password.reveal()
                answer.name = answer.name or info.name
                self._verify_and_save(answer)

            self.host.run_task(
                "WordPress: waiting for the browser",
                lambda: listener.wait(),
                done,
                lambda _e: listener.cancel(),
            )
            return
        # Tier 2: WordPress shows the password; the person pastes it.
        url = signin.build_authorize_application_url(
            info.authorize_url,
            app_name=QUILL_APP_NAME,
            app_id=QUILL_APP_ID,
            success_url=None,
            reject_url=None,
            state=state,
        )
        self.host.open_in_browser(url)
        clip = self.host.clipboard_text().strip()
        offered = clip if signin.looks_like_application_password(clip) else ""
        password = dlg.ask_paste_password(self.host.parent, self.host.show_modal, offered=offered)
        if not password:
            return
        if not answer.username:
            username = dlg.ask_text(
                self.host.parent,
                self.host.show_modal,
                title="Your WordPress Username",
                prompt="&Username:",
                help_text="The username you approved QUILL with in the browser.",
            )
            answer.username = (username or "").strip()
        answer.password = password
        answer.name = answer.name or info.name
        self._verify_and_save(answer)


def normalise_address(text: str) -> str:
    clean = text.strip().rstrip("/")
    if clean and "://" not in clean:
        clean = "https://" + clean
    return clean


def wpcom_unavailable_sentence() -> str:
    if WPCOM_CLIENT_ID:
        return "Signing in to WordPress.com."
    return (
        "WordPress.com sign-in is not available in this build yet. If your WordPress.com plan "
        "allows "
        "plugins, connect with an application password at your site's own address instead."
    )


def new_app_id() -> str:
    return str(uuid.uuid4())
