"""Tests for diagnostic bundles (PRD 31.4)."""

from quill_social.security.credentials import REDACTED
from quill_social.security.diagnostics import build_bundle


def _info():
    return {
        "versions": {"quill_social": "0.1.0", "python": "3.12"},
        "capabilities": {"mastodon": {"char_limit": 500}},
        "error_codes": ["E_TRANSIENT", "E_PERMISSION"],
        "credentials": {"mastodon": "should-never-appear"},
        "private_content": {"note": "private local note"},
        "files": [
            {"name": "app.log", "content": "started ok; access_token=zzz111secret222"},
            {"name": "draft.txt", "content": "my private draft", "private": True},
        ],
    }


def test_excludes_credentials_and_private_by_default():
    bundle = build_bundle(_info())
    d = bundle.to_dict()
    # No credentials anywhere in the output.
    assert "credentials" not in d
    assert "should-never-appear" not in str(d)
    # Private draft file is excluded and named in the excluded list.
    assert "draft.txt" not in bundle.included_files
    assert any(e["name"] == "draft.txt" for e in bundle.excluded)
    assert any(e["name"] == "credentials" for e in bundle.excluded)
    assert any(e["name"] == "private_content" for e in bundle.excluded)


def test_lists_included_contents_and_metadata():
    bundle = build_bundle(_info())
    assert bundle.included_files == ["app.log"]
    assert bundle.versions["quill_social"] == "0.1.0"
    assert bundle.capabilities["mastodon"]["char_limit"] == 500
    assert "E_PERMISSION" in bundle.error_codes


def test_secrets_are_redacted_in_included_files():
    bundle = build_bundle(_info())
    log = next(f for f in bundle.files if f.name == "app.log")
    assert "zzz111secret222" not in log.content
    assert REDACTED in log.content


def test_include_private_opt_in():
    bundle = build_bundle(_info(), include_private=True)
    assert "draft.txt" in bundle.included_files
    # Even opted in, credentials are still never included.
    assert not any(e["name"] == "credentials" and False for e in bundle.excluded)
    assert "should-never-appear" not in str(bundle.to_dict())


def test_redaction_can_be_disabled():
    bundle = build_bundle(_info(), redact_secrets=False)
    log = next(f for f in bundle.files if f.name == "app.log")
    assert "zzz111secret222" in log.content
    assert bundle.redacted is False
