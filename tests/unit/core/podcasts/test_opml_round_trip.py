"""A subscription list that arrives rich must leave rich.

Asked for on 2026-08-25: *"get all of this magical and round trippable"*.

Export used to emit only ``type``, ``text``, ``title``, ``xmlUrl`` and
``htmlUrl``, so importing somebody's OPML and exporting it again handed back a
poorer file than you were given -- descriptions, languages and categories gone,
with nothing said about it. These pin the loop shut: parse -> library ->
export -> parse must arrive at the same shows, folders and attributes.

Shared machinery, so this covers Quill Radio and QUILL Cast alike: both drive
``quill.core.podcasts``.
"""

from __future__ import annotations

from quill.core.podcasts.opml import export_opml, export_subtree, import_opml, parse_opml
from quill.core.podcasts.subscriptions import PodcastLibrary

_RICH = """<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <head><title>All Feeds</title></head>
  <body>
    <outline text="Blindness">
      <outline type="rss" text="ACB Community" title="ACB Community"
               description="Content from ACB sponsored community events."
               language="en-US" category="/Blindness,/Community"
               htmlUrl="https://acb-community.pinecast.co"
               xmlUrl="https://pinecast.com/feed/acb-community" />
    </outline>
    <outline type="rss" text="ACB Advocacy Update"
             description="Updates on advocacy efforts." language="en"
             htmlUrl="https://acb-advocacy-update.pinecast.co"
             xmlUrl="https://pinecast.com/feed/acb-advocacy-update" />
  </body>
</opml>
"""


def _round_trip(text: str) -> str:
    library = PodcastLibrary()
    import_opml(library, text)
    return export_opml(library)


def test_every_attribute_survives_the_loop() -> None:
    reimported = {show.feed_url: show for show in parse_opml(_round_trip(_RICH))}

    community = reimported["https://pinecast.com/feed/acb-community"]
    assert community.title == "ACB Community"
    assert community.description == "Content from ACB sponsored community events."
    assert community.language == "en-US"
    assert community.category == "/Blindness,/Community"
    assert community.homepage == "https://acb-community.pinecast.co"


def test_the_folder_tree_survives_the_loop() -> None:
    reimported = {show.feed_url: show for show in parse_opml(_round_trip(_RICH))}

    assert reimported["https://pinecast.com/feed/acb-community"].folder_path == ["Blindness"]
    assert reimported["https://pinecast.com/feed/acb-advocacy-update"].folder_path == []


def test_the_loop_is_stable_a_second_time_round() -> None:
    """Export -> import -> export must not keep changing the file. A round trip
    that drifts is one somebody's sync will fight with forever."""
    once = _round_trip(_RICH)
    twice = _round_trip(once)

    # dateCreated is the moment of export and is expected to differ; compare
    # what the file *says about the subscriptions*.
    assert [
        (s.title, s.feed_url, s.homepage, s.description, s.language, s.category, s.folder_path)
        for s in parse_opml(once)
    ] == [
        (s.title, s.feed_url, s.homepage, s.description, s.language, s.category, s.folder_path)
        for s in parse_opml(twice)
    ]


def test_an_absent_attribute_is_omitted_rather_than_written_empty() -> None:
    """``description=""`` asserts the feed has no description, which is a
    different claim from silence -- and a claim we would be inventing."""
    text = """<opml version="2.0"><body>
      <outline type="rss" text="Bare" xmlUrl="https://example.com/bare" />
    </body></opml>"""

    exported = _round_trip(text)

    assert "description=" not in exported
    assert "language=" not in exported
    assert "category=" not in exported


def test_the_head_carries_what_the_spec_defines_and_nothing_invented() -> None:
    """``docs`` exists in the spec for "people who might stumble across the
    file on a web server 25 years from now". Owner fields are absent on
    purpose: QUILL does not know who you are."""
    exported = _round_trip(_RICH)

    assert "<title>QUILL Podcast Subscriptions</title>" in exported
    assert "<docs>http://opml.org/spec2.opml</docs>" in exported
    assert "<dateCreated>" in exported
    assert "ownerName" not in exported
    assert "ownerEmail" not in exported


def test_exporting_one_folder_carries_the_attributes_too() -> None:
    """export_subtree had its own copy of the emit code and would otherwise
    have kept dropping them -- the reason both now share one helper."""
    library = PodcastLibrary()
    import_opml(library, _RICH)
    folder = next(f for f in library.folders if f.name == "Blindness")

    (show,) = parse_opml(export_subtree(library, folder.id))

    assert show.description == "Content from ACB sponsored community events."
    assert show.language == "en-US"
    assert show.category == "/Blindness,/Community"


def test_the_attributes_reach_the_stored_library_not_just_the_file() -> None:
    """They persist in podcasts.json, so a re-export after a restart is as
    rich as one in the same session."""
    from quill.core.podcasts.models import PodcastShow

    library = PodcastLibrary()
    import_opml(library, _RICH)
    stored = next(s for s in library.shows if s.title == "ACB Community")

    revived = PodcastShow.from_dict(stored.to_dict())

    assert revived is not None
    assert revived.description == stored.description
    assert revived.language == "en-US"
    assert revived.category == "/Blindness,/Community"
