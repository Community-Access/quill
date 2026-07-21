"""Tests for the unified safety center (PRD 27)."""

from quill_social.model import Media, SocialItem
from quill_social.services import moderation as mod


def _it(text="hello world", author="Ada", network="mock", **kw):
    return SocialItem(
        network=network,
        remote_id=kw.pop("remote_id", "1"),
        author_display=author,
        author_id=author,
        author_handle=kw.pop("author_handle", f"@{author.lower()}"),
        text=text,
        **kw,
    )


def test_matches_text():
    f = mod.Filter(criteria={"text": "spoiler"}, action="hide")
    assert mod.matches(_it(text="big SPOILER ahead"), f)
    assert not mod.matches(_it(text="nothing here"), f)


def test_matches_regex():
    f = mod.Filter(criteria={"regex": r"\bcrypto\b"}, action="warn")
    assert mod.matches(_it(text="buy crypto now"), f)
    assert not mod.matches(_it(text="cryptography is fine"), f)


def test_bad_regex_never_matches():
    f = mod.Filter(criteria={"regex": "("}, action="hide")
    assert not mod.matches(_it(text="anything"), f)


def test_matches_author():
    f = mod.Filter(criteria={"author": "grace"}, action="hide")
    assert mod.matches(_it(author="Grace"), f)
    assert not mod.matches(_it(author="Ada"), f)


def test_matches_network():
    f = mod.Filter(criteria={"network": "bluesky"}, action="hide")
    assert mod.matches(_it(network="bluesky"), f)
    assert not mod.matches(_it(network="mastodon"), f)


def test_matches_domain():
    item = _it(author_handle="@bob@spam.example")
    assert mod.matches(item, mod.Filter(criteria={"domain": "spam.example"}))
    assert not mod.matches(item, mod.Filter(criteria={"domain": "good.example"}))


def test_empty_criteria_never_matches():
    assert not mod.matches(_it(), mod.Filter(criteria={}))


def test_classify_actions():
    assert mod.classify_action("hide") == "hidden"
    assert mod.classify_action("digest_only") == "hidden"
    assert mod.classify_action("warn") == "warned"
    assert mod.classify_action("collapse") == "warned"
    assert mod.classify_action("require_reveal") == "warned"
    assert mod.classify_action("mute_speech") == "surviving"
    assert mod.classify_action("suppress_sound") == "surviving"
    assert mod.classify_action("move_to_folder") == "surviving"
    assert mod.classify_action("replace_slurs") == "surviving"


def test_apply_filters_first_match_wins():
    items = [_it(text="hide me"), _it(text="ordinary")]
    filters = [
        mod.Filter(filter_id="f1", criteria={"text": "hide me"}, action="hide"),
        mod.Filter(filter_id="f2", criteria={"text": "hide"}, action="warn"),
    ]
    outcomes = mod.apply_filters(items, filters)
    assert outcomes[0].classification == "hidden"
    assert outcomes[0].filter_id == "f1"
    assert outcomes[1].classification == "surviving"
    assert outcomes[1].filter_id == ""


def test_disabled_filter_ignored():
    f = mod.Filter(criteria={"text": "x"}, action="hide", enabled=False)
    outcomes = mod.apply_filters([_it(text="x here")], [f])
    assert outcomes[0].classification == "surviving"


def test_has_media_criterion():
    with_media = _it(media=[Media(kind="image")])
    f = mod.Filter(criteria={"has_media": True}, action="warn")
    assert mod.matches(with_media, f)
    assert not mod.matches(_it(), f)


def test_replace_slurs():
    out = mod.replace_slurs("a BadWord and badword", ["badword"], "[slur]")
    assert out == "a [slur] and [slur]"


def test_report_excludes_private_notes_by_default():
    r = mod.Report(item_id="i1", categories=["spam"], comment="see this")
    assert r.exclude_private_notes is True
    payload = r.payload(private_notes=["confidential"])
    assert payload["private_notes"] == []


def test_report_includes_notes_only_when_opted_in():
    r = mod.Report(item_id="i1", exclude_private_notes=False)
    payload = r.payload(private_notes=["shared on purpose"])
    assert payload["private_notes"] == ["shared on purpose"]


def test_safety_center_summary_counts():
    mbs = [
        mod.MuteBlock(kind="mute", target="@a"),
        mod.MuteBlock(kind="block", target="@b"),
        mod.MuteBlock(kind="block", target="@c"),
        mod.MuteBlock(kind="domain_block", target="spam.example"),
    ]
    summary = mod.safety_center_summary(
        filters=[mod.Filter()],
        muteblocks=mbs,
        reports=[mod.Report()],
        hidden_items=[_it()],
    )
    assert summary == {
        "muted": 1,
        "blocked": 2,
        "blocked_domains": 1,
        "filters": 1,
        "reports": 1,
        "hidden": 1,
    }


def test_filter_persistence_roundtrip(store):
    f = mod.Filter(name="spoilers", criteria={"text": "spoiler"}, action="hide")
    mod.save_filter(store, f)
    loaded = mod.load_filters(store)
    assert len(loaded) == 1
    assert loaded[0].name == "spoilers"
    assert loaded[0].criteria == {"text": "spoiler"}
    mod.delete_filter(store, f.filter_id)
    assert mod.load_filters(store) == []


def test_muteblock_and_report_persistence(store):
    mod.save_muteblock(store, mod.MuteBlock(kind="block", target="@troll"))
    mod.save_report(store, mod.Report(item_id="i9", categories=["abuse"]))
    assert len(mod.load_muteblocks(store)) == 1
    assert mod.load_muteblocks(store)[0].kind == "block"
    assert len(mod.load_reports(store)) == 1
