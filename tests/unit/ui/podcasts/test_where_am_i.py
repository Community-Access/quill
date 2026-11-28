"""Where Am I? in QUILL Cast (Ctrl+Shift+W), and Say Current Episode's longer line.

Jeff, 2026-11-27: there was no key that said where he was in an episode.
"""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.podcasts.chapters import PodcastChapter
from quill.ui.podcasts import where_am_i


class _Controller:
    def __init__(self, position: int = 1_004_000, length: int = 3_480_000) -> None:
        self.state = SimpleNamespace(episode_guid="ep")
        self._position = position
        self._length = length

    def position_ms(self) -> int:
        return self._position

    def length_ms(self) -> int:
        return self._length


def _host(**extra) -> SimpleNamespace:
    said: list[str] = []
    host = SimpleNamespace(
        _podcast_controller=_Controller(),
        _podcast_current_chapters=[
            PodcastChapter(start_ms=0, title="Welcome"),
            PodcastChapter(start_ms=754_000, title="Listener mail"),
            PodcastChapter(start_ms=1_144_000, title="Goodbye"),
        ],
        _announce=lambda text, force=False: said.append(text),
        said=said,
    )
    for name, value in extra.items():
        setattr(host, name, value)
    return host


def test_it_says_the_chapter_then_the_episode() -> None:
    host = _host()
    where_am_i.say_where_am_i(host)
    assert host.said == [
        "Listener mail, 4 minutes 10 into the chapter, 2 minutes 20 left. "
        "16 minutes 44 of 58 minutes, 41 minutes 16 left."
    ]


def test_pressed_twice_quickly_it_copies(monkeypatch) -> None:
    copied: list[str] = []
    monkeypatch.setattr(
        "quill.ui.say_commands.set_clipboard_text", lambda t: copied.append(t) or True
    )
    host = _host()
    where_am_i.say_where_am_i(host)
    where_am_i.say_where_am_i(host)
    assert copied and copied[0].startswith("Listener mail, 4 minutes 10")
    assert host.said[-1] == "Copied where you are."
    where_am_i.say_where_am_i(host)  # a third press speaks again
    assert host.said[-1].startswith("Listener mail")


def test_nothing_playing_says_so() -> None:
    host = _host(_podcast_controller=None)
    where_am_i.say_where_am_i(host)
    assert host.said == ["Nothing is playing."]


def test_say_current_episode_adds_the_chapter_and_the_time() -> None:
    line = where_am_i.now_playing_sentence(_host(), "Podcasts: playing Thursday")
    assert line == "Podcasts: playing Thursday, in Listener mail, 16:44 of 58:00."


def test_say_current_episode_with_nothing_playing() -> None:
    host = _host(_podcast_controller=None)
    assert where_am_i.now_playing_sentence(host, "Podcasts: stopped") == "Podcasts: stopped"
