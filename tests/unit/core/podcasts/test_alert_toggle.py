"""The row's alert toggle: which way it points, and what it can never do.

The property worth pinning is the one that makes this safe to put one
keystroke from a podcast row: **it can never reach "off"**. Off is the mode
that stops recording a new episode anywhere, and it stays in settings where
somebody chose it deliberately. The toggle moves between on and quiet, and
both of those still write the notification -- so pressing it by accident, in
either direction, cannot cost anybody an episode.

The other half is the label. It says what pressing it *does*, never what is
currently true: a menu item that reports state reads to a screen reader as a
claim about the row, and the listener discovers it was a verb by pressing it.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.podcasts import alert_toggle, episode_alerts
from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.models_settings import PodcastSettings
from quill.core.podcasts.subscriptions import load_library, new_id, save_library
from quill.core.radio.podcast_follow import show_menu_facts, toggle_alert_for_feed

FEED = "https://feeds.example/show"


def _seed(tmp_path: Path, *, alert: str | None = None) -> str:
    library = load_library(tmp_path)
    show = PodcastShow(id=new_id(), title="The Allusionist", feed_url=FEED)
    library.add_show(show)
    if alert is not None:
        library.apply_show_override(show, new_episode_alert=alert)
    save_library(tmp_path, library)
    return show.id


# -- the label ---------------------------------------------------------------


def test_the_label_names_the_action_not_the_state() -> None:
    assert alert_toggle.menu_label(True) == "Stop &Notifying About This Podcast"
    assert alert_toggle.menu_label(False) == "&Notify Me About This Podcast"


def test_the_label_keeps_one_mnemonic_in_both_directions() -> None:
    """The row's menu is rebuilt each time it opens; a mnemonic that moved with
    the state would be a key that works only half the time."""
    on, off = alert_toggle.menu_label(True), alert_toggle.menu_label(False)
    assert on[on.index("&") + 1].upper() == off[off.index("&") + 1].upper() == "N"


# -- what it reads ------------------------------------------------------------


class _Library:
    def __init__(self, settings: PodcastSettings) -> None:
        self._settings = settings
        self.written: dict[str, object] = {}

    def effective_settings(self, _show: object) -> PodcastSettings:
        return self._settings

    def apply_show_override(self, _show: object, **updates: object) -> None:
        self.written.update(updates)


def test_it_reads_the_effective_mode_not_the_shows_own() -> None:
    """A folder that turned alerts on has already decided; a menu reading only
    the show's override would offer to turn on something already on."""
    library = _Library(PodcastSettings(new_episode_alert=episode_alerts.ALERT_ON))
    assert alert_toggle.alert_now(library, object()) == episode_alerts.ALERT_ON


def test_an_unreadable_chain_reads_as_the_shipped_default() -> None:
    class _Broken:
        def effective_settings(self, _show: object) -> PodcastSettings:
            raise RuntimeError("settings chain is broken")

    assert alert_toggle.alert_now(_Broken(), object()) == episode_alerts.ALERT_DEFAULT


# -- what it writes -----------------------------------------------------------


def test_on_becomes_quiet_and_quiet_becomes_on() -> None:
    loud = _Library(PodcastSettings(new_episode_alert=episode_alerts.ALERT_ON))
    assert alert_toggle.toggle(loud, object()) == episode_alerts.ALERT_QUIET

    hushed = _Library(PodcastSettings(new_episode_alert=episode_alerts.ALERT_QUIET))
    assert alert_toggle.toggle(hushed, object()) == episode_alerts.ALERT_ON


def test_a_show_set_to_off_is_turned_on_not_toggled_towards_silence() -> None:
    """Somebody who went looking for this verb on a silent show wants to hear
    about it. The toggle answers that rather than reading "off" as "not on"
    and leaving it where it was."""
    silent = _Library(PodcastSettings(new_episode_alert=episode_alerts.ALERT_OFF))
    assert alert_toggle.toggle(silent, object()) == episode_alerts.ALERT_ON


def test_it_never_writes_off() -> None:
    """The safety property: neither direction can stop an episode being
    recorded. Off stays a deliberate choice made in settings."""
    for mode in (episode_alerts.ALERT_ON, episode_alerts.ALERT_QUIET, episode_alerts.ALERT_OFF):
        library = _Library(PodcastSettings(new_episode_alert=mode))
        alert_toggle.toggle(library, object())
        assert library.written["new_episode_alert"] != episode_alerts.ALERT_OFF


def test_it_writes_only_the_alert_field() -> None:
    """A whole-record write would freeze this podcast's every other setting at
    whatever the shared default happened to be today."""
    library = _Library(PodcastSettings())
    alert_toggle.toggle(library, object())
    assert list(library.written) == ["new_episode_alert"]


# -- the sentence -------------------------------------------------------------


def test_turning_it_off_says_what_still_happens() -> None:
    """Otherwise it reads as "you will not hear about this show again", and the
    listener stops trusting the quiet mode."""
    spoken = alert_toggle.outcome_sentence("The Allusionist", episode_alerts.ALERT_QUIET)
    assert "Notifications" in spoken
    assert spoken.startswith("The Allusionist")


def test_a_nameless_show_still_gets_a_sentence() -> None:
    assert alert_toggle.outcome_sentence("", episode_alerts.ALERT_ON).startswith("This podcast")


# -- through the library, on disk ---------------------------------------------


def test_the_row_verb_saves_and_reads_back_the_other_way(tmp_path: Path) -> None:
    _seed(tmp_path)
    assert show_menu_facts(tmp_path, FEED)[3] == episode_alerts.ALERT_DEFAULT

    spoken = toggle_alert_for_feed(tmp_path, FEED)
    assert "will notify you" in spoken
    assert show_menu_facts(tmp_path, FEED)[3] == episode_alerts.ALERT_ON

    toggle_alert_for_feed(tmp_path, FEED)
    assert show_menu_facts(tmp_path, FEED)[3] == episode_alerts.ALERT_QUIET


def test_a_feed_that_is_no_longer_followed_says_nothing_rather_than_lying(tmp_path: Path) -> None:
    """A menu can outlive the subscription behind it -- unsubscribing in Quill
    Cast while the row menu is open is enough."""
    assert toggle_alert_for_feed(tmp_path, FEED) == ""


def test_the_menu_facts_answer_from_one_read_and_never_raise(tmp_path: Path) -> None:
    assert show_menu_facts(tmp_path, "") == (0, 0, "", "")
    _seed(tmp_path, alert=episode_alerts.ALERT_ON)
    unheard, episodes, title, alert = show_menu_facts(tmp_path, FEED)
    assert (unheard, episodes, title, alert) == (0, 0, "The Allusionist", episode_alerts.ALERT_ON)
