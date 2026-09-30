"""What a notification points back at, and the one shape that must keep working.

The back-compat case is the whole reason this module exists rather than a
``partition(":")`` at the call site. Two ways to get it wrong, both silent:

* **A bare id must read as a show.** 3.1.0's first notices stored the show id
  with no prefix and are sitting in people's files right now. Refusing them
  would make Enter do nothing on exactly the notifications somebody already
  has, which is indistinguishable from the bug this was built to fix.
* **A stream URL must not be read as a kind.** ``https://x/y`` splits on its
  first colon into ``("https", "//x/y")``, so a parser that trusts whatever is
  before the colon invents a kind nothing handles and opens nothing at all.
"""

from __future__ import annotations

from quill.core import notification_targets as nt


def test_a_bare_id_is_a_show_because_that_is_what_shipped() -> None:
    assert nt.parse("abc123") == (nt.KIND_SHOW, "abc123")


def test_a_prefixed_show_reads_back_as_written() -> None:
    assert nt.parse(nt.for_show("abc123")) == (nt.KIND_SHOW, "abc123")


def test_a_stream_url_is_not_mistaken_for_a_kind() -> None:
    target = nt.for_stream("https://stream.example/live")
    assert nt.parse(target) == (nt.KIND_STREAM, "https://stream.example/live")


def test_an_unknown_prefix_is_an_id_not_a_kind() -> None:
    """A colon in an id is an id with a colon in it, not a vocabulary word."""
    assert nt.parse("itunes:12345") == (nt.KIND_SHOW, "itunes:12345")


def test_nothing_to_open_reads_as_nothing() -> None:
    for empty in ("", "   ", None, "show:", "stream:  "):
        assert nt.parse(empty) == ("", "")  # type: ignore[arg-type]


def test_a_target_with_no_id_is_never_written() -> None:
    """Better an empty target than one that opens the wrong row later."""
    assert nt.for_show("") == ""
    assert nt.for_show("   ") == ""
    assert nt.for_stream("") == ""


def test_the_ids_are_trimmed_on_the_way_in_and_out() -> None:
    assert nt.for_show("  abc  ") == "show:abc"
    assert nt.parse("show:  abc  ") == (nt.KIND_SHOW, "abc")
