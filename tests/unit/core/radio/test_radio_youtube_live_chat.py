"""YouTube Live Chat, the wx-free half: rows, emoji, links, speech, pause, the reader."""

from __future__ import annotations

from quill.core.radio import youtube_live_chat as lc
from quill.core.radio import youtube_live_chat_reader as reader_mod


def _raw(name="Sam", text="great show", *, badges=(), money=None, kind="text_message", **extra):
    raw = {
        "message_id": f"{name}-{text}",
        "message": text,
        "message_type": kind,
        "author": {"name": name, "id": "UC" + name, "badges": list(badges)},
    }
    if money:
        raw["money"] = {"text": money}
    raw.update(extra)
    return raw


def _msg(name="Sam", text="hello", **kwargs) -> lc.ChatMessage:
    message = lc.parse_message(_raw(name, text, **kwargs))
    assert message is not None
    return message


# -- rows read author, message, labels ------------------------------------------


def test_row_reads_author_then_message_then_labels() -> None:
    message = _msg(badges=[{"title": "Moderator", "icon_name": "moderator"}], text="great show")
    assert lc.row_label(message) == "Sam: great show, moderator"


def test_paid_owner_and_member_labels_in_reading_order() -> None:
    message = _msg(
        "Ann",
        "thanks!",
        money="$5.00",
        kind="paid_message",
        badges=[{"title": "Member (6 months)"}, {"icon_name": "owner"}],
    )
    assert lc.row_label(message) == "Ann: thanks!, paid $5.00, owner, member"
    assert message.is_paid and message.is_important


def test_time_is_on_demand_not_in_the_row() -> None:
    message = _msg(timestamp=1_700_000_000_000_000, time_text="3:13 PM")
    assert "PM" not in lc.row_label(message)
    assert "sent at" in lc.full_text(message)


def test_replay_offset_reads_as_time_into_the_stream() -> None:
    message = _msg(time_in_seconds=3723.0)
    assert lc.when_said(message) == "1:02:03 into the stream"


def test_emoji_become_names_and_runs_are_counted() -> None:
    said = lc.emoji_to_text("hi\U0001f600there \U0001f602\U0001f602\U0001f602 ❤️")
    assert said == "hi :grinning_face: there :face_with_tears_of_joy: x3 :heavy_black_heart:"


def test_custom_emote_names_from_chat_downloader_are_kept() -> None:
    # chat-downloader already writes a channel emote as its name.
    assert lc.row_label(_msg(text=":yt: nice :hand-pink-waving:")).endswith(
        ":yt: nice :hand-pink-waving:"
    )


def test_links_read_as_links_in_the_row_and_whole_in_full_text() -> None:
    message = _msg(text="see https://www.example.com/page. now")
    assert lc.row_label(message) == "Sam: see link example.com/page. now"
    assert "https://www.example.com/page" in lc.full_text(message)


def test_empty_and_malformed_messages_are_dropped() -> None:
    assert lc.parse_message({"message": "", "author": {"name": "x"}}) is None
    assert lc.parse_message("nonsense") is None


def test_same_author_jumps_both_ways() -> None:
    rows = [_msg("A", "1"), _msg("B", "2"), _msg("A", "3"), _msg("C", "4")]
    assert lc.same_author_index(rows, 0, 1) == 2
    assert lc.same_author_index(rows, 2, -1) == 0
    assert lc.same_author_index(rows, 3, 1) == -1


def test_filter_needs_every_word() -> None:
    rows = [_msg("A", "the bridge in bristol"), _msg("B", "a bridge")]
    assert [m.author for m in lc.filter_messages(rows, "bristol bridge")] == ["A"]


# -- speaking: rate limit, coalescing, priority, quiet hours ---------------------


class _Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def _announcer(mode=lc.SPEAK_ALL, word="", held=lambda: False):
    said: list[str] = []
    clock = _Clock()
    announcer = lc.ChatAnnouncer(said.append, clock=clock, held_back=held)
    announcer.mode = mode
    announcer.word = word
    return announcer, said, clock


def test_off_by_default_says_nothing() -> None:
    said: list[str] = []
    announcer = lc.ChatAnnouncer(said.append)
    announcer.offer([_msg()])
    announcer.tick()
    assert said == []


def test_a_burst_is_one_sentence_with_a_count() -> None:
    announcer, said, clock = _announcer()
    announcer.offer([_msg("A", "first")])
    assert said == ["A: first."]
    announcer.offer([_msg(str(i), "x") for i in range(12)])
    assert len(said) == 1, "inside the gap nothing more is said"
    clock.now += lc.MIN_GAP_SECONDS
    announcer.tick()
    assert said[-1] == "12 new messages."


def test_never_more_than_once_per_gap() -> None:
    announcer, said, clock = _announcer()
    for step in range(20):
        announcer.offer([_msg(str(step), "x")])
        clock.now += 0.5
        announcer.tick()
    # 10 seconds of chat: at most one sentence per MIN_GAP_SECONDS, plus the first.
    assert len(said) <= int(10 / lc.MIN_GAP_SECONDS) + 1


def test_paid_message_keeps_its_words_inside_a_burst() -> None:
    announcer, said, clock = _announcer(mode=lc.SPEAK_ALL)
    clock.now = 0.0
    announcer._last = -1.0  # inside the gap: everything waits
    announcer.offer([_msg("A", "hi"), _msg("Ann", "thanks", money="$5.00"), _msg("B", "yo")])
    clock.now = 10.0
    announcer.tick()
    assert said == ["Ann: thanks, paid $5.00. And 2 more messages."]


def test_a_mention_is_spoken_even_when_only_important_ones_are_chosen() -> None:
    announcer, said, _clock = _announcer(mode=lc.SPEAK_IMPORTANT, word="Jeff")
    announcer.offer([_msg("A", "ordinary"), _msg("B", "hello Jeff!")])
    assert said == ["B: hello Jeff!"]


def test_mentions_mode_ignores_everything_else() -> None:
    announcer, said, _clock = _announcer(mode=lc.SPEAK_MENTIONS, word="bridge")
    announcer.offer([_msg("A", "nothing here"), _msg("B", "bridges")])
    assert said == []


def test_quiet_hours_drop_rather_than_save_up() -> None:
    quiet = {"on": True}
    announcer, said, clock = _announcer(held=lambda: quiet["on"])
    announcer.offer([_msg()])
    assert said == [] and announcer.waiting == 0
    quiet["on"] = False
    clock.now += 100
    announcer.tick()
    assert said == []


# -- pause and resume ------------------------------------------------------------


def test_pause_counts_and_resume_releases_in_order() -> None:
    feed = lc.ChatFeed()
    assert feed.add([_msg("A", "1")])
    feed.pause()
    assert feed.add([_msg("B", "2"), _msg("C", "3")]) == []
    assert feed.unseen == 2
    released = feed.resume()
    assert [m.author for m in released] == ["B", "C"]
    assert [m.author for m in feed.messages] == ["A", "B", "C"]
    assert feed.unseen == 0


def test_feed_trims_the_oldest_past_its_cap() -> None:
    feed = lc.ChatFeed(cap=3)
    feed.add([_msg(str(i), "x") for i in range(5)])
    assert feed.trim() == 2
    assert [m.author for m in feed.messages] == ["2", "3", "4"]


def test_replay_released_in_step_with_playback() -> None:
    early, late = _msg("A", "1", time_in_seconds=5.0), _msg("B", "2", time_in_seconds=50.0)
    due, waiting = lc.release_replay([early, late], 10.0)
    assert due == [early] and waiting == [late]


# -- the reader thread, with a fake chat-downloader -----------------------------


def test_reader_queues_messages_and_ends() -> None:
    ended: list[bool] = []

    def opener(_url):
        return iter([_raw("A", "one"), _raw("B", "two")]), lambda: None

    reader = reader_mod.ChatReader("u", opener=opener, on_end=lambda: ended.append(True))
    reader.run()
    assert [m.author for m in reader.drain()] == ["A", "B"]
    assert ended == [True]


def test_a_final_failure_is_said_once_without_retrying() -> None:
    class NoChatReplay(Exception):
        pass

    calls: list[str] = []
    errors: list[str] = []

    def opener(url):
        calls.append(url)
        raise NoChatReplay("none")

    reader = reader_mod.ChatReader("u", opener=opener, on_error=errors.append)
    reader.run()
    assert len(calls) == 1
    assert errors == [reader_mod.speakable(NoChatReplay())]
    assert reader.failed


def test_transient_failures_retry_politely_then_stop() -> None:
    calls: list[str] = []
    errors: list[str] = []

    def opener(url):
        calls.append(url)
        raise ConnectionError("connection reset")

    reader = reader_mod.ChatReader(
        "u", opener=opener, on_error=errors.append, retry_waits=(0.0, 0.0)
    )
    reader.run()
    assert len(calls) == 3  # first try + two retries
    assert errors == ["YouTube could not be reached. Check your connection."]


def test_stop_closes_the_session() -> None:
    closed: list[bool] = []

    def endless():
        while True:
            yield _raw()

    reader = reader_mod.ChatReader("u", opener=lambda _u: (endless(), lambda: closed.append(True)))
    reader.start()
    reader.stop(timeout=2.0)
    assert closed == [True]
    assert not reader.running


def test_safe_mode_refuses_before_import(monkeypatch) -> None:
    import pytest

    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    with pytest.raises(lc.LiveChatError):
        reader_mod.open_chat("https://www.youtube.com/watch?v=abcdefghijk")
