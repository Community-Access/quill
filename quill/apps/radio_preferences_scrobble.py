"""Preferences' Scrobbling and Song recognition rows.

Its own module because ``radio_preferences`` is near its GATE-11 ceiling, and
because these rows share a shape: a switch kept in Radio's settings, and a
token kept in the Windows credential store, never in a settings file.

* **Scrobbling** -- send the songs you hear for a minute or more to
  ListenBrainz, last.fm or Libre.fm. Each is off until you turn it on.
  ListenBrainz takes a pasted user token; last.fm and Libre.fm sign in through
  the browser (:mod:`quill.ui.radio.scrobble_signin`).
* **Song recognition service** -- AcoustID (the default) or AudD, and the AudD
  token. Recognition still only runs when you choose Identify This Song.

No access keys: this dialog has no letter left that is not already taken, and
a duplicate would be worse than none (GATE-14). The ideas come from BlindRadio
by serrebidev (MIT).
"""

from __future__ import annotations

import webbrowser
from typing import Any

from quill.core.radio import audd, lastfm, listenbrainz, radio_credentials, scrobbling
from quill.core.radio import song_recognition as recognition

SCROBBLE_GROUP = "Scrobbling"
RECOGNITION_GROUP = "Song recognition"

LISTENBRAINZ_CHECK = "Send the songs I hear to ListenBrainz"
LISTENBRAINZ_CHECK_HELP = (
    "Off by default. When on, each song you hear for a minute or more is added "
    "to your ListenBrainz listening history: its artist, title and album, and "
    "when you heard it. Needs your ListenBrainz user token below. " + scrobbling.PRIVACY_NOTE
)
LASTFM_CHECK = "Send the songs I hear to last.fm"
LASTFM_CHECK_HELP = (
    "Off by default. When on, each song you hear for a minute or more is "
    "scrobbled to your last.fm account, and the song you are hearing shows as "
    "now playing on your profile. Choose Sign In to last.fm first. " + scrobbling.PRIVACY_NOTE
)
LIBREFM_CHECK = "Send the songs I hear to Libre.fm"
LIBREFM_CHECK_HELP = (
    "Off by default. The same as last.fm, for a Libre.fm account. Choose Sign "
    "In to Libre.fm first. " + scrobbling.PRIVACY_NOTE
)

LISTENBRAINZ_TOKEN = "ListenBrainz user token:"
LISTENBRAINZ_TOKEN_HELP = (
    f"Your own ListenBrainz user token, from {listenbrainz.TOKEN_URL}. Kept in "
    "the Windows credential store, not in a settings file; clear the box to "
    "remove it."
)
LASTFM_KEY = "last.fm API key (only if you have your own):"
LASTFM_KEY_HELP = (
    "Signing in to last.fm or Libre.fm needs a last.fm API key and shared "
    "secret. If this copy of Quill Radio came with one, leave this blank. "
    f"Otherwise make a free API account at {lastfm.API_ACCOUNT_URL} and paste "
    "its API key here. Kept in the Windows credential store."
)
LASTFM_SECRET = "last.fm shared secret (only if you have your own):"
LASTFM_SECRET_HELP = (
    "The shared secret that goes with your own last.fm API key. Leave it blank "
    "when the key box is blank. Kept in the Windows credential store."
)
AUDD_TOKEN = "AudD API token:"
AUDD_TOKEN_HELP = (
    f"Your own AudD API token, from {audd.DASHBOARD_URL}, used only when Song "
    "recognition service is AudD. Kept in the Windows credential store; clear "
    "the box to remove it."
)
SERVICE_LABEL = "Song recognition service:"
SERVICE_HELP = (
    "Which service Identify This Song asks. AcoustID, the default, is sent a "
    "fingerprint of the audio, which cannot be played back, and needs a free "
    "AcoustID key. AudD is sent about twenty seconds of the audio itself and "
    "needs your own AudD API token; it copes better with live radio. Either "
    "way, nothing is sent until you choose Identify This Song."
)

SIGN_IN_HELP = (
    "Opens {name}'s own page in your web browser to let Quill Radio scrobble "
    "for you; you sign in there, never here. When you are signed in already, "
    "this offers to sign you out instead. Works at once, whether or not you "
    "then choose OK."
)
API_ACCOUNT_LABEL = "Get a last.fm API Account..."
API_ACCOUNT_HELP = (
    f"Opens {lastfm.API_ACCOUNT_URL} in your web browser, where last.fm gives "
    "you a free API key and shared secret to paste into the two boxes above."
)


class ScrobbleRows:
    """The rows, and what to do with their answers."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self.dialog: Any = None
        self._key_index = -1
        self._secret_index = -1
        history = app._radio_history
        self._before = {
            "lb": radio_credentials.load(radio_credentials.LISTENBRAINZ_TOKEN).secret,
            "key": radio_credentials.load(radio_credentials.LASTFM_API_KEY).secret,
            "secret": radio_credentials.load(radio_credentials.LASTFM_SECRET).secret,
            "audd": audd.stored_token(),
        }
        self._history = history

    # -- the rows ---------------------------------------------------------

    def checkboxes(self) -> list[Any]:
        from quill.ui.app_preferences_dialog import PreferenceCheckbox

        history = self._history
        return [
            PreferenceCheckbox(
                LISTENBRAINZ_CHECK,
                LISTENBRAINZ_CHECK_HELP,
                history.scrobble_listenbrainz,
                group=SCROBBLE_GROUP,
            ),
            PreferenceCheckbox(
                LASTFM_CHECK, LASTFM_CHECK_HELP, history.scrobble_lastfm, group=SCROBBLE_GROUP
            ),
            PreferenceCheckbox(
                LIBREFM_CHECK, LIBREFM_CHECK_HELP, history.scrobble_librefm, group=SCROBBLE_GROUP
            ),
        ]

    def choice(self) -> Any:
        from quill.ui.app_preferences_dialog import PreferenceChoice

        return PreferenceChoice(
            SERVICE_LABEL,
            SERVICE_HELP,
            [label for _service, label in recognition.SERVICE_CHOICES],
            recognition.service_index(self._history.recognition_service),
            group=RECOGNITION_GROUP,
        )

    def texts(self) -> list[Any]:
        """``[ListenBrainz token, last.fm key, last.fm secret, AudD token]``."""
        from quill.ui.app_preferences_dialog import PreferenceText

        return [
            PreferenceText(
                LISTENBRAINZ_TOKEN,
                LISTENBRAINZ_TOKEN_HELP,
                self._before["lb"],
                group=SCROBBLE_GROUP,
            ),
            PreferenceText(LASTFM_KEY, LASTFM_KEY_HELP, self._before["key"], group=SCROBBLE_GROUP),
            PreferenceText(
                LASTFM_SECRET, LASTFM_SECRET_HELP, self._before["secret"], group=SCROBBLE_GROUP
            ),
            PreferenceText(
                AUDD_TOKEN, AUDD_TOKEN_HELP, self._before["audd"], group=RECOGNITION_GROUP
            ),
        ]

    def actions(self) -> list[Any]:
        from quill.ui.app_preferences_dialog import PreferenceAction

        return [
            PreferenceAction(
                f"Sign In to {lastfm.LASTFM.name}...",
                SIGN_IN_HELP.format(name=lastfm.LASTFM.name),
                lambda: self.sign_in(lastfm.LASTFM),
                group=SCROBBLE_GROUP,
            ),
            PreferenceAction(
                f"Sign In to {lastfm.LIBREFM.name}...",
                SIGN_IN_HELP.format(name=lastfm.LIBREFM.name),
                lambda: self.sign_in(lastfm.LIBREFM),
                group=SCROBBLE_GROUP,
            ),
            PreferenceAction(
                API_ACCOUNT_LABEL, API_ACCOUNT_HELP, self.open_api_account, group=SCROBBLE_GROUP
            ),
        ]

    def attach(self, dialog: Any, *, first_text_index: int) -> None:
        """Let the sign-in buttons read the key boxes as they are, unsaved."""
        self.dialog = dialog
        self._key_index = first_text_index + 1
        self._secret_index = first_text_index + 2

    # -- the buttons ------------------------------------------------------

    def _typed_pair(self) -> tuple[str, str]:
        if self.dialog is None or self._key_index < 0:
            return self._before["key"], self._before["secret"]
        return (
            self.dialog.text_value(self._key_index),
            self.dialog.text_value(self._secret_index),
        )

    def sign_in(self, service: lastfm.Service) -> None:
        from quill.ui.radio import scrobble_commands, scrobble_signin

        scrobble_signin.sign_in(
            self.app,
            service,
            self._typed_pair,
            after=lambda: scrobble_commands.refresh_accounts(self.app),
        )

    def open_api_account(self) -> None:
        try:
            webbrowser.open(lastfm.API_ACCOUNT_URL)
        except Exception:  # noqa: BLE001 - the address is in the help either way
            self.app._announce(f"Open {lastfm.API_ACCOUNT_URL} in your web browser.")

    # -- applying ---------------------------------------------------------

    def apply(self, checks: list[bool], choice_index: int, texts: list[str]) -> str:
        """Save what came back. Returns a sentence for "Preferences saved", or ""."""
        history = self._history
        said: list[str] = []
        lb_on, fm_on, libre_on = (bool(value) for value in checks)
        history.scrobble_listenbrainz = lb_on
        history.scrobble_lastfm = fm_on
        history.scrobble_librefm = libre_on
        index = min(max(0, int(choice_index)), len(recognition.SERVICE_CHOICES) - 1)
        history.recognition_service = recognition.SERVICE_CHOICES[index][0]
        lb_token, key, secret, audd_token = (text.strip() for text in texts)
        failed = False
        for target, new, old in (
            (radio_credentials.LISTENBRAINZ_TOKEN, lb_token, self._before["lb"]),
            (radio_credentials.LASTFM_API_KEY, key, self._before["key"]),
            (radio_credentials.LASTFM_SECRET, secret, self._before["secret"]),
        ):
            if new != old and not radio_credentials.save(target, new):
                failed = True
        if audd_token != self._before["audd"] and not audd.save_token(audd_token):
            failed = True
        if failed:
            said.append("A token could not be saved on this computer.")
        if lb_on and not lb_token:
            said.append("ListenBrainz is on, but there is no user token yet.")
        for on, service in ((fm_on, lastfm.LASTFM), (libre_on, lastfm.LIBREFM)):
            if on and not radio_credentials.load(service.session_target).secret:
                said.append(f"{service.name} is on, but you have not signed in yet.")
        if history.recognition_service == recognition.SERVICE_AUDD and not audd_token:
            said.append("Song recognition is set to AudD, but there is no AudD token yet.")
        from quill.ui.radio import scrobble_commands

        scrobble_commands.refresh_accounts(self.app)
        return " ".join(said)


__all__ = ["RECOGNITION_GROUP", "SCROBBLE_GROUP", "ScrobbleRows"]
