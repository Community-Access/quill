"""What Find Streams says about a checked scan: one sentence, distinct rows."""

from __future__ import annotations

from quill.core.radio.find_streams_text import row_status, status_label, summary_sentence
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


def test_a_live_row_with_no_name_falls_back_to_the_host() -> None:
    assert row_status(_c("https://stream.example.org/a", "live", codec="AAC")) == (
        "Live: stream.example.org, AAC"
    )


def test_not_checked_rows_say_why_so_they_can_be_told_apart() -> None:
    row = _c("u", "not checked", check_note="it took too long to answer")
    assert row_status(row) == "Not checked: it took too long to answer"
    assert row_status(_c("https://s.example/x")) == "Not checked: s.example"


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
    assert summary_sentence(rows, checked=True) == "Found 3 live streams and 2 not checked."
    rows.append(_c("f", "file"))
    assert summary_sentence(rows, checked=True) == (
        "Found 3 live streams, 2 not checked and 1 audio file."
    )
    assert summary_sentence([_c("a", "live")], checked=True) == "Found 1 live stream."


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
