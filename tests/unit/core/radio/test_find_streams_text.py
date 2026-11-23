"""What Find Streams says about a checked scan: one sentence, distinct rows."""

from __future__ import annotations

from quill.core.radio.find_streams_text import row_status, status_label, summary_sentence
from quill.core.radio.live_check import OUT_OF_TIME, TOO_MANY
from quill.core.radio.page_links import PageStreamCandidate
from quill.core.radio.stream_pick import pick_stream


def _c(url: str, check: str = "", **fields: object) -> PageStreamCandidate:
    candidate = PageStreamCandidate(url=url, reason="audio tag", check=check)
    for name, value in fields.items():
        setattr(candidate, name, value)
    return candidate


def test_a_live_row_names_the_stream_codec_and_bitrate() -> None:
    row = _c("https://s.example/live", "live", stream_name="WXYZ FM", codec="MP3", bitrate_kbps=128)
    assert row_status(row) == "Live: WXYZ FM, MP3, 128 kbps"


def test_a_live_row_with_no_name_falls_back_to_its_address() -> None:
    # The last part of the path tells two streams on one host apart...
    assert row_status(_c("https://stream.example.org/jazz", "live", codec="AAC")) == (
        "Live: jazz on stream.example.org, AAC"
    )
    # ...and a bare host is all there is to say.
    assert row_status(_c("https://stream.example.org/", "live", codec="AAC")) == (
        "Live: stream.example.org, AAC"
    )


def test_a_directory_name_is_used_when_the_stream_sends_none() -> None:
    named = _c("https://s.example/live", "live", label="WXYZ Community", label_is_name=True)
    assert row_status(named) == "Live: WXYZ Community"
    # A page's link text is not a station name, so it is not read as one.
    link_text = _c("https://s.example/live", "live", label="Click here")
    assert row_status(link_text) == "Live: live on s.example"
    sent = _c("https://s.example/live", "live", stream_name="KXYZ", label="X", label_is_name=True)
    assert row_status(sent) == "Live: KXYZ"


def test_not_checked_rows_keep_the_name_and_say_why() -> None:
    row = _c("https://s.example/u", "not checked", check_note="it took too long to answer")
    assert row_status(row) == "Not checked: u on s.example, it took too long to answer"
    capital = _c(
        "https://media-ssl.musicradio.com/CapitalUK",
        "not checked",
        label="Capital UK",
        label_is_name=True,
        check_note="there were too many links to check them all",
    )
    assert row_status(capital) == (
        "Not checked: Capital UK, there were too many links to check them all"
    )
    assert row_status(_c("https://s.example/")) == "Not checked: s.example"


def test_listener_counts_read_naturally() -> None:
    assert row_status(_c("https://s.example/", "live", listeners=0)) == (
        "Live: s.example, no listeners"
    )
    assert row_status(_c("https://s.example/", "live", listeners=1234)) == (
        "Live: s.example, 1,234 listeners"
    )


def test_an_audio_file_row_says_it_is_not_live() -> None:
    assert row_status(_c("https://p.example/e.mp3", "file", codec="MP3")).startswith(
        "Audio file, not a live stream"
    )


def test_the_sentence_counts_in_list_order() -> None:
    rows = [
        _c("a", "live"),
        _c("b", "live"),
        _c("c", "live"),
        _c("d", "not checked"),
        _c("e", "not checked"),
    ]
    assert summary_sentence(rows, checked=True) == "Found 3 live streams and 2 links not checked."
    rows.append(_c("f", "file"))
    assert summary_sentence(rows, checked=True) == (
        "Found 3 live streams, 2 links not checked and 1 audio file."
    )
    assert summary_sentence([_c("a", "live")], checked=True) == "Found 1 live stream."


def test_the_sentence_says_when_the_scans_own_limits_left_links_unchecked() -> None:
    over = [_c(str(n), "live") for n in range(12)] + [
        _c(f"x{n}", "not checked", check_note=TOO_MANY) for n in range(36)
    ]
    assert summary_sentence(over, checked=True, check_limit=48) == (
        "Found 12 live streams and 36 links not checked, because one scan checks at most 48 links."
    )
    late = [_c("a", "live"), _c("b", "not checked", check_note=OUT_OF_TIME)]
    assert summary_sentence(late, checked=True) == (
        "Found 1 live stream and 1 link not checked, because checking stops after 20 seconds."
    )
    # A server's own refusal is the row's to say, not the sentence's.
    refused = [_c("a", "live"), _c("b", "not checked", check_note="it took too long to answer")]
    assert summary_sentence(refused, checked=True) == "Found 1 live stream and 1 link not checked."
    # Still one sentence (GATE-13), even with no live streams at all.
    only = [_c("b", "not checked", check_note=TOO_MANY)]
    assert summary_sentence(only, checked=True, check_limit=16) == (
        "Found 1 link; it could not be checked, because one scan checks at most 16 links."
    )


def test_nothing_could_be_checked() -> None:
    assert summary_sentence([_c("a", "not checked")], checked=True) == (
        "Found 1 link; it could not be checked."
    )
    assert summary_sentence([_c("a", "not checked"), _c("b", "not checked")], checked=True) == (
        "Found 2 links; none could be checked."
    )


def test_everything_proven_not_audio_is_its_own_result() -> None:
    assert summary_sentence([], checked=True, left_out=4) == (
        "Found 4 links on that page, but none of them were audio."
    )
    assert summary_sentence([], checked=True) == "No stream links were found on that page."


def test_left_out_links_are_shown_but_not_spoken_while_rows_exist() -> None:
    rows = [_c("a", "live")]
    assert "Left out" not in summary_sentence(rows, checked=True, left_out=2)
    assert status_label(rows, checked=True, left_out=2) == (
        "Found 1 live stream. Left out 2 links that were not audio or no longer there."
    )


def test_pick_stream_prefers_a_checked_live_stream_and_never_a_file() -> None:
    assert pick_stream([_c("a", "not checked"), _c("b", "live")]).url == "b"
    assert pick_stream([_c("pod.mp3", "file"), _c("b", "not checked")]).url == "b"
    # Unchecked candidates behave exactly as before.
    assert not pick_stream([_c("a"), _c("b")]).found


def test_one_link_left_out_is_said_the_right_way_round() -> None:
    assert summary_sentence([], checked=True, left_out=1) == (
        "Found 1 link on that page, but it was not audio."
    )


def test_a_failure_is_said_in_plain_words_never_raw_exception_text() -> None:
    import socket
    import urllib.error

    from quill.core.radio.find_streams_text import failure_sentence
    from quill.core.radio.link_finder import LinkFinderError

    def wrapped(cause: BaseException) -> LinkFinderError:
        error = LinkFinderError(f"Could not reach that page: {cause}")
        error.__cause__ = cause
        return error

    assert failure_sentence(None) == "Could not scan that page."
    assert failure_sentence(wrapped(urllib.error.URLError(socket.gaierror(11001, "x")))) == (
        "Could not scan that page: QUILL could not find that website."
    )
    assert failure_sentence(wrapped(urllib.error.URLError(TimeoutError()))).endswith(
        "took too long to answer."
    )
    assert failure_sentence(LinkFinderError("Type a website address to scan.")) == (
        "Type a website address to scan."
    )
    assert "<" not in failure_sentence(RuntimeError("<urlopen error [Errno 11001]>"))
