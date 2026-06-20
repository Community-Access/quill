from __future__ import annotations

import hmac
import json

from quill.core.updates import (
    _MANIFEST_KEY_ENV,
    DEFAULT_UPDATE_MANIFEST_URL,
    GitHubRelease,
    is_newer_version,
    parse_update_manifest,
    select_latest,
)

_TEST_DEPLOY_KEY = "quill-test-deploy-key-for-unit-tests"


def _signed_payload(version: str, download_url: str, published_at: str, notes: str) -> str:
    canonical = json.dumps(
        {
            "download_url": download_url,
            "notes": notes,
            "published_at": published_at,
            "version": version,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    signature = hmac.new(
        _TEST_DEPLOY_KEY.encode("utf-8"),
        canonical.encode("utf-8"),
        "sha256",
    ).hexdigest()
    return json.dumps({
        "version": version,
        "download_url": download_url,
        "published_at": published_at,
        "notes": notes,
        "signature": signature,
    })


def test_parse_update_manifest_accepts_valid_signature(monkeypatch) -> None:
    monkeypatch.setenv(_MANIFEST_KEY_ENV, _TEST_DEPLOY_KEY)
    payload = _signed_payload(
        "1.2.3",
        "https://community-access.github.io/quill/releases/download/v1.2.3/Quill-Setup.exe",
        "2026-05-01",
        "Fixes.",
    )
    manifest = parse_update_manifest(payload)
    assert manifest.version == "1.2.3"
    assert manifest.download_url.endswith("/Quill-Setup.exe")


def test_parse_update_manifest_rejects_bad_signature() -> None:
    payload = json.dumps({
        "version": "1.2.3",
        "download_url": "https://community-access.github.io/quill/releases/download/v1.2.3/Quill-Setup.exe",
        "published_at": "2026-05-01",
        "notes": "Fixes.",
        "signature": "bad",
    })
    try:
        parse_update_manifest(payload)
    except ValueError as exc:
        assert "signature verification failed" in str(exc)
    else:
        raise AssertionError("Expected signature verification failure")


def test_is_newer_version_compares_semver_triplets() -> None:
    assert is_newer_version("0.1.0", "0.2.0") is True
    assert is_newer_version("1.2.3", "1.2.3") is False


def test_final_release_outranks_its_prereleases() -> None:
    # A final build is newer than any pre-release of the same x.y.z.
    assert is_newer_version("1.2.0-rc1", "1.2.0") is True
    assert is_newer_version("1.2.0", "1.2.0-rc1") is False


def test_display_form_beta_is_recognized_as_newer_than_release() -> None:
    """The display version ("0.7.0 Beta 1") is what build_info emits.

    Without the space-form parser the running 0.7.0 beta build would
    compare ``0.7.0 Beta 1`` against the manifest's ``0.7.0`` and never
    see "update available" when a newer beta ships.
    """
    # Beta 1 was released before the stable 0.7.0, so a user on stable
    # is NOT outdated by beta 1.
    assert is_newer_version("0.7.0 Beta 1", "0.7.0") is True
    assert is_newer_version("0.7.0", "0.7.0 Beta 1") is False
    # Beta 2 is newer than beta 1; running beta 1 should see beta 2.
    assert is_newer_version("0.7.0 Beta 1", "0.7.0 Beta 2") is True
    assert is_newer_version("0.7.0 Beta 2", "0.7.0 Beta 2") is False


def test_display_form_release_candidate_is_recognized() -> None:
    assert is_newer_version("0.7.0 Beta 1", "0.7.0 Release Candidate 1") is True
    assert is_newer_version("0.7.0 Release Candidate 1", "0.7.0") is True


def test_display_form_final_outranks_display_form_prerelease() -> None:
    assert is_newer_version("0.7.0 Release Candidate 1", "0.7.0") is True
    assert is_newer_version("0.7.0", "0.7.0 Release Candidate 1") is False


def test_prerelease_stages_order_rc_above_beta_above_alpha() -> None:
    assert is_newer_version("1.2.0-beta1", "1.2.0-rc1") is True
    assert is_newer_version("1.2.0-alpha1", "1.2.0-beta1") is True
    assert is_newer_version("1.2.0-rc1", "1.2.0-rc2") is True


def test_prerelease_suffix_does_not_leak_into_patch_number() -> None:
    # "1.2.0-rc1" must not be read as patch 1, which would outrank 1.2.0.
    assert is_newer_version("1.2.0", "1.2.0-rc1") is False


def _release(version: str, *, prerelease: bool) -> GitHubRelease:
    return GitHubRelease(
        version=version,
        download_url="https://example.invalid/x",
        published_at="2026-01-01",
        notes="",
        prerelease=prerelease,
    )


def test_select_latest_prefers_final_over_prerelease() -> None:
    releases = [
        _release("1.2.0-rc1", prerelease=True),
        _release("1.2.0", prerelease=False),
    ]
    latest = select_latest(releases, include_prereleases=True)
    assert latest is not None and latest.version == "1.2.0"


def test_default_update_manifest_url_points_to_hidden_pages_feed() -> None:
    assert DEFAULT_UPDATE_MANIFEST_URL.startswith("https://community-access.github.io/quill/")
    assert "/updates/." in DEFAULT_UPDATE_MANIFEST_URL


def test_parse_update_manifest_rejects_untrusted_download_host() -> None:
    payload = _signed_payload("1.2.3", "https://example.com/download", "2026-05-01", "Fixes.")
    try:
        parse_update_manifest(payload)
    except ValueError as exc:
        assert "not trusted" in str(exc)
    else:
        raise AssertionError("Expected trusted-host validation failure")


def test_download_release_asset_reports_streaming_progress(tmp_path, monkeypatch) -> None:
    from quill.core import updates

    body = b"x" * (200 * 1024)  # 200 KiB across multiple 64 KiB chunks

    class _FakeResponse:
        def __init__(self) -> None:
            self.headers = {"Content-Length": str(len(body))}
            self._offset = 0

        def __enter__(self) -> _FakeResponse:
            return self

        def __exit__(self, *exc: object) -> None:
            return None

        def read(self, size: int = -1) -> bytes:
            if size is None or size < 0:
                chunk = body[self._offset :]
                self._offset = len(body)
                return chunk
            chunk = body[self._offset : self._offset + size]
            self._offset += len(chunk)
            return chunk

    monkeypatch.setattr(updates, "urlopen", lambda *a, **k: _FakeResponse())
    monkeypatch.setattr(updates, "_validate_remote_url", lambda url: None)

    seen: list[tuple[int, int]] = []
    destination = tmp_path / "quill-setup.exe"
    updates.download_release_asset(
        "https://github.com/releases/download/x",
        destination,
        progress=lambda done, total: seen.append((done, total)),
    )

    assert destination.read_bytes() == body
    assert seen[0] == (0, len(body))
    assert seen[-1] == (len(body), len(body))
    assert len(seen) > 2  # streamed in multiple chunks, not one read


def test_salt_only_signature_rejected(monkeypatch) -> None:
    # M-6: verify_manifest_signature must return False when no deployment key
    # is configured (QUILL_UPDATE_MANIFEST_KEY absent). Salt-only HMAC is a
    # placeholder and must never be treated as trusted.
    import hashlib

    monkeypatch.delenv("QUILL_UPDATE_MANIFEST_KEY", raising=False)

    from quill.core.updates import _SIGNATURE_SALT, UpdateManifest, verify_manifest_signature

    manifest_data = {
        "download_url": "https://example.com/quill.exe",
        "notes": "patch",
        "published_at": "2026-06-09",
        "version": "1.0.1",
    }
    canonical = json.dumps(manifest_data, separators=(",", ":"), sort_keys=True)
    salt_sig = hmac.new(_SIGNATURE_SALT.encode(), canonical.encode(), hashlib.sha256).hexdigest()

    m = UpdateManifest(
        version="1.0.1",
        download_url="https://example.com/quill.exe",
        notes="patch",
        published_at="2026-06-09",
        signature=salt_sig,
    )
    assert not verify_manifest_signature(m), "salt-only signature must be rejected"
