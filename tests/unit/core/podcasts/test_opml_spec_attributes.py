"""What OPML 2.0 defines, against what our importer actually reads.

Checked against the spec itself (``http://opml.org/spec2.opml``) on
2026-08-25, after Jeff asked "are there any other attributes of the OPML
standard that are missing from our import tool?".

The spec's own words for a subscription list:

    Required attributes: type, text, xmlUrl.
    Optional attributes: description, htmlUrl, language, title, version.
    These attributes are useful when presenting a list of subscriptions to a
    user, except for version, they are all derived from information in the
    feed itself.

"Useful when presenting a list of subscriptions to a user" is a description of
the ACB Media Podcasts picker, so the presentation attributes are read now
rather than left on the floor.
"""

from __future__ import annotations

from quill.core.podcasts.opml import parse_opml

_FULL = """<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <head><title>All Feeds</title></head>
  <body>
    <outline type="rss" text="ACB Community" title="ACB Community"
             description="Content from ACB sponsored community events."
             language="en-US" version="RSS2" category="/Blindness,/Community"
             htmlUrl="https://acb-community.pinecast.co"
             xmlUrl="https://pinecast.com/feed/acb-community" />
  </body>
</opml>
"""


def test_the_presentation_attributes_are_read() -> None:
    (show,) = parse_opml(_FULL)

    assert show.title == "ACB Community"
    assert show.feed_url == "https://pinecast.com/feed/acb-community"
    assert show.homepage == "https://acb-community.pinecast.co"
    assert show.description == "Content from ACB sponsored community events."
    assert show.language == "en-US"
    assert show.category == "/Blindness,/Community"


def test_category_is_kept_verbatim_rather_than_split() -> None:
    """OPML allows categories *and* nested outlines. Flattening the string
    would quietly lose the difference between one slash-delimited path and two
    separate tags -- the spec's own examples are "/Boston/Weather" and
    "/Harvard/Berkman,/Politics"."""
    (show,) = parse_opml(_FULL)

    assert show.category == "/Blindness,/Community"


def test_a_commented_outline_is_ignored_as_the_spec_requires() -> None:
    """Spec: "isComment is a string, either "true" or "false", indicating
    whether the outline is commented or not."

    We used to subscribe to it, which turns somebody's parked feed back on
    behind their back.
    """
    text = """<opml version="2.0"><body>
      <outline type="rss" text="Parked" isComment="true"
               xmlUrl="https://example.com/parked" />
      <outline type="rss" text="Live" xmlUrl="https://example.com/live" />
    </body></opml>"""

    titles = [show.title for show in parse_opml(text)]

    assert titles == ["Live"]


def test_commenting_a_folder_comments_everything_under_it() -> None:
    """Spec: "By convention if an outline is commented, all subordinate
    outlines are considered to also be commented"."""
    text = """<opml version="2.0"><body>
      <outline text="Parked folder" isComment="true">
        <outline type="rss" text="Inside" xmlUrl="https://example.com/inside" />
      </outline>
      <outline type="rss" text="Live" xmlUrl="https://example.com/live" />
    </body></opml>"""

    titles = [show.title for show in parse_opml(text)]

    assert titles == ["Live"]


def test_isComment_false_or_absent_imports_normally() -> None:
    """Spec: "If it's not present, the value is false." Only the literal
    "true" may suppress a feed -- anything else and we would be dropping
    subscriptions somebody asked for."""
    text = """<opml version="2.0"><body>
      <outline type="rss" text="A" isComment="false" xmlUrl="https://example.com/a" />
      <outline type="rss" text="B" xmlUrl="https://example.com/b" />
      <outline type="rss" text="C" isComment="" xmlUrl="https://example.com/c" />
    </body></opml>"""

    assert [show.title for show in parse_opml(text)] == ["A", "B", "C"]


def test_a_file_without_the_optional_attributes_still_imports() -> None:
    """ACB's own link.acb.org copy carries no description, language or
    category. Absent is not empty-is-an-error."""
    text = """<opml version="2.0"><body>
      <outline type="rss" text="Advocacy Update" xmlUrl="https://example.com/a" />
    </body></opml>"""

    (show,) = parse_opml(text)

    assert (show.description, show.language, show.category) == ("", "", "")


def test_summary_is_accepted_where_an_exporter_used_rss_wording() -> None:
    text = """<opml version="2.0"><body>
      <outline type="rss" text="A" summary="From RSS" xmlUrl="https://example.com/a" />
    </body></opml>"""

    (show,) = parse_opml(text)

    assert show.description == "From RSS"


def test_nested_outlines_still_carry_their_folder_path() -> None:
    """The spec's "categorized subscription lists that are arbitrarily
    structured" -- unchanged by the new attributes."""
    text = """<opml version="2.0"><body>
      <outline text="Blindness">
        <outline text="ACB">
          <outline type="rss" text="Community" xmlUrl="https://example.com/c" />
        </outline>
      </outline>
    </body></opml>"""

    (show,) = parse_opml(text)

    assert show.folder_path == ["Blindness", "ACB"]
