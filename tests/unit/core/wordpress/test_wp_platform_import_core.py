"""Blogger, Medium, Substack and Squarespace exports, read here and imported as drafts."""

from __future__ import annotations

import io
import zipfile

import pytest

from quill.core.wordpress import platform_import as pi
from quill.core.wordpress.wxr_import import plan_import, send_import
from tests.unit.core.wordpress.test_wp_wxr_core import NEW, ImportApi

BLOGGER = b"""<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns='http://www.w3.org/2005/Atom' xmlns:app='http://purl.org/atom/app#'>
<title type='text'>Ann's Garden</title>
<link rel='alternate' type='text/html' href='https://anngarden.blogspot.com/'/>
<entry>
  <category scheme='http://schemas.google.com/g/2005#kind'
    term='http://schemas.google.com/blogger/2008/kind#post'/>
  <category scheme='http://www.blogger.com/atom/ns#' term='Roses'/>
  <published>2019-04-02T09:30:00.000-07:00</published>
  <title type='text'>Spring roses</title>
  <content type='html'>&lt;p&gt;Look:&lt;/p&gt;&lt;img src="https://blogger.googleusercontent.com/r.jpg"/&gt;</content>
  <link rel='alternate' type='text/html'
    href='https://anngarden.blogspot.com/2019/04/spring-roses.html'/>
  <author><name>Ann</name><email>noreply@blogger.com</email></author>
</entry>
<entry>
  <category scheme='http://schemas.google.com/g/2005#kind'
    term='http://schemas.google.com/blogger/2008/kind#post'/>
  <published>2019-05-01T00:00:00.000-07:00</published>
  <title type='text'>Half written</title>
  <content type='html'>&lt;p&gt;Later.&lt;/p&gt;</content>
  <app:control><app:draft>yes</app:draft></app:control>
  <author><name>Ann</name></author>
</entry>
<entry>
  <category scheme='http://schemas.google.com/g/2005#kind'
    term='http://schemas.google.com/blogger/2008/kind#comment'/>
  <title type='text'>Nice!</title><content type='html'>hi</content>
</entry>
<entry>
  <category scheme='http://schemas.google.com/g/2005#kind'
    term='http://schemas.google.com/blogger/2008/kind#settings'/>
  <title type='text'>x</title><content type='text'>y</content>
</entry>
</feed>
"""

MEDIUM_STORY = """<!DOCTYPE html><html><head><title>Why we moved</title></head><body>
<article class="h-entry"><header><h1 class="p-name">Why we moved</h1></header>
<section data-field="subtitle" class="p-summary">A short story</section>
<section data-field="body" class="e-content"><section name="a1" class="section">
<div class="section-content"><h3 class="graf graf--h3 graf--title">Why we moved</h3>
<p class="graf">We moved.</p><img src="https://cdn-images-1.medium.com/max/800/a.png"/>
</div></section></section>
<footer><p>By <a href="https://medium.com/@sam" class="p-author h-card">Sam Lee</a> on
<a href="https://medium.com/p/x"><time class="dt-published" datetime="2021-06-07T10:11:12.000Z">
June 7</time></a>.</p><p><a href="https://medium.com/@sam/why-we-moved-1a2b3c4d5e6f"
class="p-canonical">Canonical link</a></p></footer></article></body></html>"""


def _zip(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, text in files.items():
            archive.writestr(name, text)
    return buffer.getvalue()


MEDIUM = _zip({
    "README.html": "<p>Your data</p>",
    "posts/2021-06-07_Why-we-moved-1a2b3c4d5e6f.html": MEDIUM_STORY,
    "posts/draft_Next-time-0f0f0f0f0f0f.html": MEDIUM_STORY.replace("Why we moved", "Next time"),
    "../evil/posts/x.html": "<p>outside</p>",
})

SUBSTACK = _zip({
    "posts.csv": (
        "post_id,post_date,is_published,email_sent_at,inbox_sent_at,type,audience,title,"
        "subtitle,podcast_url\n"
        "101.hello-world,2022-01-03T12:00:00.000Z,true,,,newsletter,everyone,Hello world,"
        "First one,\n"
        "102.paid-notes,2022-02-03T12:00:00.000Z,true,,,newsletter,only_paid,Paid notes,,\n"
        "103.episode-one,2022-03-03T12:00:00.000Z,false,,,podcast,everyone,Episode one,,"
        "https://api.substack.com/feed/podcast/103.mp3\n"
        "104.a-thread,2022-04-03T12:00:00.000Z,true,,,thread,everyone,A thread,,\n"
    ),
    "posts/101.hello-world.html": '<p>Hi.</p><img src="https://substackcdn.com/image/h.png">',
    "posts/102.paid-notes.html": "<p>For you.</p>",
    "posts/103.episode-one.html": "<p>Show notes.</p>",
    "email_list.csv": "email\nx@example.org\n",
})

SQUARESPACE = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:wp="http://wordpress.org/export/1.2/"
 xmlns:content="http://purl.org/rss/1.0/modules/content/"
 xmlns:excerpt="http://wordpress.org/export/1.2/excerpt/"
 xmlns:dc="http://purl.org/dc/elements/1.1/">
<channel><title>Bakery</title><link>https://bakery.example</link>
<generator>Squarespace</generator>
<item><title>Opening day</title><link>/blog/opening-day</link>
<dc:creator>chef</dc:creator>
<content:encoded><![CDATA[<div class="sqs-block"><p>See <a href="/menu">the menu</a>.</p>
<img src="https://images.squarespace-cdn.com/b.jpg"/></div>]]></content:encoded>
<wp:post_id>1</wp:post_id><wp:post_date>2020-02-02 10:00:00</wp:post_date>
<wp:post_name></wp:post_name><wp:status>publish</wp:status><wp:post_type>post</wp:post_type>
</item>
<item><title>Menu</title><link>/menu</link>
<content:encoded><![CDATA[<p>Bread</p>]]></content:encoded>
<wp:post_id>2</wp:post_id><wp:post_name>menu</wp:post_name><wp:status>publish</wp:status>
<wp:post_type>page</wp:post_type></item>
</channel></rss>
"""


@pytest.mark.parametrize(
    ("data", "platform"),
    [
        (BLOGGER, "blogger"),
        (MEDIUM, "medium"),
        (SUBSTACK, "substack"),
        (SQUARESPACE, "squarespace"),
    ],
    ids=["blogger", "medium", "substack", "squarespace"],
)
def test_each_export_is_recognised(data, platform) -> None:
    assert pi.detect(data) == platform


def test_blogger_posts_labels_and_drafts_and_what_is_left_out() -> None:
    got = pi.read_export(BLOGGER, "blog.xml")
    assert got.name == "Blogger"
    first, second = got.wxr.items
    assert (first.title, first.slug, first.status) == ("Spring roses", "spring-roses", "publish")
    assert first.terms == [("post_tag", "roses", "Roses")]
    assert first.date == "2019-04-02T09:30:00" and "blogger.googleusercontent.com" in first.content
    assert second.status == "draft"
    assert [a.login for a in got.wxr.authors] == ["Ann"] and got.wxr.authors[0].email == ""
    notes = "\n".join(got.notes)
    assert "blogger.googleusercontent.com" in notes and "nothing is downloaded" in notes
    assert "1 of them were drafts on Blogger." in notes
    assert "Left out: 1 Blogger comment entries" in notes
    assert "Left out: 1 Blogger settings entries" in notes


def test_medium_stories_keep_their_subtitle_author_and_date_and_skip_outside_names() -> None:
    got = pi.read_export(MEDIUM, "medium.zip")
    titles = {i.title: i for i in got.wxr.items}
    assert set(titles) == {"Why we moved", "Next time"}
    story = titles["Why we moved"]
    assert story.slug == "why-we-moved" and story.excerpt == "A short story"
    assert story.creator == "Sam Lee" and story.date == "2021-06-07 10:11:12"
    assert '<p class="graf">We moved.</p>' in story.content and "graf--title" not in story.content
    assert "<footer" not in story.content
    assert titles["Next time"].status == "draft"
    assert "outside" not in "".join(i.content for i in got.wxr.items)
    assert any("cdn-images-1.medium.com" in n for n in got.notes)


def test_substack_rows_with_bodies_paid_podcasts_and_threads() -> None:
    got = pi.read_export(SUBSTACK, "substack.zip")
    by_title = {i.title: i for i in got.wxr.items}
    assert list(by_title) == ["Hello world", "Paid notes", "Episode one"]
    assert by_title["Hello world"].slug == "hello-world"
    assert by_title["Hello world"].excerpt == "First one"
    assert by_title["Episode one"].status == "draft"
    assert '<audio controls src="https://api.substack.com/feed/podcast/103.mp3">' in (
        by_title["Episode one"].content
    )
    notes = "\n".join(got.notes)
    assert "1 were for paying subscribers only" in notes
    assert "1 of them were never published on Substack." in notes
    assert "Left out: 1 threads" in notes and "Subscribers are not imported" in notes


def test_squarespace_without_a_version_has_its_relative_addresses_made_whole() -> None:
    got = pi.read_export(SQUARESPACE, "bakery.xml")
    post, page = got.wxr.items
    assert got.wxr.blog_url == "https://bakery.example"
    assert 'href="https://bakery.example/menu"' in post.content
    assert '<div class="sqs-block">' in post.content  # its own markup kept
    assert post.slug == "opening-day" and post.link == "https://bakery.example/blog/opening-day"
    assert any("1 addresses" in n for n in got.notes)


def test_a_plain_wordpress_export_reads_as_itself() -> None:
    from tests.unit.core.wordpress.test_wp_wxr_core import _item, _wxr

    got = pi.read_export(_wxr(_item(1, "post", "Hi")), "site.xml")
    assert got.platform == "wordpress" and [i.title for i in got.wxr.items] == ["Hi"]


@pytest.mark.parametrize(
    ("data", "words"),
    [
        (b"hello", "not an export QUILL knows"),
        (_zip({"notes.txt": "x"}), "not an export QUILL knows"),
        (b"PK\x03\x04broken", "not an export QUILL knows"),
        (b"<feed xmlns='http://www.w3.org/2005/Atom'><entry>", "not a readable Blogger backup"),
    ],
    ids=["text", "other-zip", "broken-zip", "broken-atom"],
)
def test_what_is_not_an_export_is_one_sentence_with_its_own_code(data, words) -> None:
    with pytest.raises(pi.PlatformExportError) as caught:
        pi.read_export(data, "x")
    assert words in caught.value.plain
    assert pi.PlatformExportError.code == "QUILL-WP-IMPORT-PLATFORM-UNREADABLE"


def test_a_zip_with_too_many_files_is_refused(monkeypatch) -> None:
    monkeypatch.setattr(pi, "MAX_MEMBERS", 2)
    with pytest.raises(pi.PlatformExportError, match="more than 2 files"):
        pi.read_medium(MEDIUM, "medium.zip")


def test_a_converted_export_is_imported_as_drafts_through_the_wxr_import() -> None:
    api = ImportApi()
    got = pi.read_export(SUBSTACK, "substack.zip")
    plan = plan_import(api, got.wxr)
    assert [i.title for i in plan.items] == ["Hello world", "Paid notes", "Episode one"]
    assert not plan.attachments and not plan.unmatched
    send_import(api, plan, here=NEW, fetch=None)
    made = [b for _m, r, b in api.writes if r == "wp/v2/posts"]
    assert {b["status"] for b in made} == {"draft"} and {b["author"] for b in made} == {7}
    assert "https://substackcdn.com/image/h.png" in made[0]["content"]
