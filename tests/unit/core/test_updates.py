from __future__ import annotations

import hmac
import json

from quill.core.updates import (
    _MANIFEST_KEY_ENV,
    DEFAULT_UPDATE_MANIFEST_URL,
    FeatureAdvisory,
    GitHubRelease,
    UpdateManifest,
    _pick_asset,
    active_feature_locks,
    is_newer_version,
    manifest_signature,
    parse_update_manifest,
    select_latest,
)


def _release_assets() -> list[dict]:
    """Assets mirroring a real windows-release: installer, portable zip, and the
    unrelated delta update zip plus a metadata json."""
    return [
        {
            "name": "Quill-for-All-Setup-0.8.0.exe",
            "browser_download_url": "https://example.test/Quill-for-All-Setup-0.8.0.exe",
        },
        {
            "name": "Quill-Portable-v0.8.0.zip",
            "browser_download_url": "https://example.test/Quill-Portable-v0.8.0.zip",
        },
        {
            "name": "quill-v0.8.0-update-windows.zip",
            "browser_download_url": "https://example.test/quill-v0.8.0-update-windows.zip",
        },
        {
            "name": "sbom.json",
            "browser_download_url": "https://example.test/sbom.json",
        },
    ]


def _force_windows_suffixes(monkeypatch) -> None:
    # Asset selection past the portable branch is platform-specific; pin it to the
    # Windows installer order so these tests are deterministic on Linux CI too.
    monkeypatch.setattr(
        "quill.core.updates._platform_asset_suffixes",
        lambda: (".exe", ".msi", ".zip"),
    )


def test_pick_asset_portable_prefers_portable_zip() -> None:
    # The portable branch runs before any platform-specific ordering.
    url = _pick_asset(_release_assets(), prefer_portable=True)
    assert url == "https://example.test/Quill-Portable-v0.8.0.zip"


def test_pick_asset_installed_prefers_installer_exe(monkeypatch) -> None:
    _force_windows_suffixes(monkeypatch)
    url = _pick_asset(_release_assets(), prefer_portable=False)
    assert url == "https://example.test/Quill-for-All-Setup-0.8.0.exe"


def test_pick_asset_portable_falls_back_to_installer_without_portable_zip(monkeypatch) -> None:
    _force_windows_suffixes(monkeypatch)
    assets = [a for a in _release_assets() if "portable" not in a["name"].lower()]
    url = _pick_asset(assets, prefer_portable=True)
    assert url == "https://example.test/Quill-for-All-Setup-0.8.0.exe"


def test_pick_asset_never_returns_a_foreign_platform_asset(monkeypatch) -> None:
    # A release whose Windows build failed in CI and only published a macOS
    # asset must never hand that .dmg to a Windows client.
    _force_windows_suffixes(monkeypatch)
    assets = [{"name": "Quill.dmg", "browser_download_url": "https://example.test/Quill.dmg"}]
    assert _pick_asset(assets, prefer_portable=False) == ""
    assert _pick_asset(assets, prefer_portable=True) == ""


def test_select_latest_skips_release_with_no_platform_asset() -> None:
    releases = [
        GitHubRelease(
            version="0.9.0-beta.3",
            download_url="https://example.test/Quill.dmg",
            published_at="2026-07-12",
            notes="",
            prerelease=True,
            has_platform_asset=False,
        ),
        GitHubRelease(
            version="0.9.0-beta.2",
            download_url="https://example.test/Quill-for-All-Setup-0.9.0.Beta.2.exe",
            published_at="2026-07-11",
            notes="",
            prerelease=True,
            has_platform_asset=True,
        ),
    ]
    latest = select_latest(releases, include_prereleases=True)
    assert latest is not None and latest.version == "0.9.0-beta.2"


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


def test_interim_patch_build_sorts_between_prereleases() -> None:
    """An interim hand-off build ("Beta 1A") sits strictly between Beta 1 and
    Beta 2, so a tester on it is offered the real Beta 2 but is never nagged to
    "update" back down to the published Beta 1.
    """
    # Strict ordering: Beta 1 < Beta 1A < Beta 2.
    assert is_newer_version("0.8.0 Beta 1", "0.8.0 Beta 1A") is True
    assert is_newer_version("0.8.0 Beta 1A", "0.8.0 Beta 2") is True
    # On Beta 1A: the live Beta 1 feed is NOT an update; Beta 2 IS.
    assert is_newer_version("0.8.0 Beta 1A", "0.8.0 Beta 1") is False
    assert is_newer_version("0.8.0 Beta 1A", "0.8.0 Beta 2") is True
    # The interim build does not outrank the final stable release either.
    assert is_newer_version("0.8.0 Beta 1A", "0.8.0") is True


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


def test_signer_and_verifier_agree_without_key(monkeypatch) -> None:
    # The publisher and the client share quill.core.updates.manifest_signature,
    # so the feed the publisher writes always verifies. With no deployment key
    # configured (the deployed baseline) that is the salt-only signature; a
    # tampered signature is still rejected.
    monkeypatch.delenv("QUILL_UPDATE_MANIFEST_KEY", raising=False)

    from quill.core.updates import UpdateManifest, manifest_signature, verify_manifest_signature

    fields = {
        "version": "1.0.1",
        "download_url": "https://example.com/quill.exe",
        "published_at": "2026-06-09",
        "notes": "patch",
    }
    good = UpdateManifest(signature=manifest_signature(**fields), **fields)
    assert verify_manifest_signature(good), "publisher's salt-only signature must verify"

    tampered = UpdateManifest(signature="0" * 64, **fields)
    assert not verify_manifest_signature(tampered), "a forged signature must be rejected"


def test_keyed_mode_requires_hmac_not_salt(monkeypatch) -> None:
    # When a deployment key IS configured on the client, only the keyed HMAC
    # signature is accepted; the salt-only baseline is no longer sufficient.
    from quill.core.updates import UpdateManifest, manifest_signature, verify_manifest_signature

    fields = {
        "version": "1.0.1",
        "download_url": "https://example.com/quill.exe",
        "published_at": "2026-06-09",
        "notes": "patch",
    }
    salt_only = manifest_signature(**fields)  # no key
    keyed = manifest_signature(**fields, key="deploy-secret")

    monkeypatch.setenv("QUILL_UPDATE_MANIFEST_KEY", "deploy-secret")
    assert verify_manifest_signature(UpdateManifest(signature=keyed, **fields))
    assert not verify_manifest_signature(UpdateManifest(signature=salt_only, **fields))


def test_resolve_endpoints_default_to_production(monkeypatch) -> None:
    # Release-rehearsal overrides must be inert unless explicitly set, so a normal
    # user always hits the production endpoints.
    from quill.core.updates import (
        GITHUB_RELEASES_API,
        resolve_manifest_url,
        resolve_releases_api_url,
    )

    monkeypatch.delenv("QUILL_UPDATE_API_URL", raising=False)
    monkeypatch.delenv("QUILL_UPDATE_MANIFEST_URL", raising=False)
    assert resolve_releases_api_url() == GITHUB_RELEASES_API
    assert resolve_manifest_url() == DEFAULT_UPDATE_MANIFEST_URL


def test_resolve_endpoints_honour_overrides(monkeypatch) -> None:
    # Setting the env vars redirects discovery to a throwaway repo/feed.
    from quill.core.updates import resolve_manifest_url, resolve_releases_api_url

    api = "https://api.github.com/repos/Community-Access/quill-update-selftest/releases"
    feed = "https://community-access.github.io/quill-update-selftest/feed.json"
    monkeypatch.setenv("QUILL_UPDATE_API_URL", api)
    monkeypatch.setenv("QUILL_UPDATE_MANIFEST_URL", feed)
    assert resolve_releases_api_url() == api
    assert resolve_manifest_url() == feed


def test_resolve_endpoints_strip_accidental_surrounding_quotes(monkeypatch) -> None:
    # A value set via `setx VAR "https://..."` (or copied with quotes) arrives
    # wrapped in literal quotes; urllib then fails with 'unknown url type: "https'.
    # The resolver must strip a single surrounding quote pair so the override works.
    from quill.core.updates import resolve_manifest_url, resolve_releases_api_url

    api = "https://api.github.com/repos/Community-Access/quill-update-selftest/releases"
    feed = "https://community-access.github.io/quill-update-selftest/feed.json"
    monkeypatch.setenv("QUILL_UPDATE_API_URL", f'"{api}"')
    monkeypatch.setenv("QUILL_UPDATE_MANIFEST_URL", f"'{feed}'")
    assert resolve_releases_api_url() == api
    assert resolve_manifest_url() == feed


def test_fetch_releases_uses_api_override(monkeypatch) -> None:
    # The override must actually reach the network call, not just the resolver:
    # fetch_releases() with no explicit api_url queries the overridden endpoint.
    from quill.core import updates

    override = "https://api.github.com/repos/Community-Access/quill-update-selftest/releases"
    monkeypatch.setenv("QUILL_UPDATE_API_URL", override)

    seen: dict[str, str] = {}

    class _FakeResponse:
        def __enter__(self) -> _FakeResponse:
            return self

        def __exit__(self, *exc: object) -> None:
            return None

        def read(self) -> bytes:
            return b"[]"

    def _fake_urlopen(request, *args, **kwargs):  # noqa: ANN001
        seen["url"] = request.full_url if hasattr(request, "full_url") else str(request)
        return _FakeResponse()

    monkeypatch.setattr(updates, "urlopen", _fake_urlopen)
    assert updates.fetch_releases() == []
    assert seen["url"] == override


# --------------------------------------------------------------------------- #
# Remote feature kill switch (signed advisories in the update manifest)
# --------------------------------------------------------------------------- #
def _signed_feed(advisories: tuple[FeatureAdvisory, ...] = ()) -> str:
    version = "0.9.0"
    url = "https://github.com/Community-Access/quill/releases/download/latest/x.exe"
    sig = manifest_signature(
        version=version, download_url=url, published_at="", notes="", advisories=advisories
    )
    body: dict = {
        "version": version,
        "download_url": url,
        "published_at": "",
        "notes": "",
        "signature": sig,
    }
    if advisories:
        body["advisories"] = [
            {
                "feature_id": a.feature_id,
                "reason": a.reason,
                "min_version": a.min_version,
                "max_version": a.max_version,
                "advisory_id": a.advisory_id,
            }
            for a in advisories
        ]
    return json.dumps(body)


def test_manifest_with_no_advisories_still_verifies() -> None:
    # Backward compatibility: an existing feed with no advisories keeps its
    # old signature (advisories key omitted from the signed canonical form).
    m = parse_update_manifest(_signed_feed())
    assert m.version == "0.9.0" and m.advisories == ()


def test_signed_advisory_round_trips_and_verifies() -> None:
    adv = FeatureAdvisory(feature_id="core.glow", reason="crash", max_version="0.9.5")
    m = parse_update_manifest(_signed_feed((adv,)))
    assert len(m.advisories) == 1 and m.advisories[0].feature_id == "core.glow"


def test_tampered_advisory_fails_signature() -> None:
    import pytest

    adv = FeatureAdvisory(feature_id="core.glow", reason="crash")
    feed = json.loads(_signed_feed((adv,)))
    # Attacker swaps the locked feature id but cannot re-sign.
    feed["advisories"][0]["feature_id"] = "core.everything"
    with pytest.raises(ValueError, match="signature"):
        parse_update_manifest(json.dumps(feed))


def test_active_feature_locks_respects_version_range() -> None:
    m = UpdateManifest(
        version="0.9.0",
        download_url="x",
        published_at="",
        notes="",
        signature="",
        advisories=(
            FeatureAdvisory(feature_id="a", reason="ra", max_version="0.9.5"),
            FeatureAdvisory(feature_id="b", reason="rb", min_version="1.0.0"),
            FeatureAdvisory(feature_id="c", reason=""),  # unbounded
        ),
    )
    locks = active_feature_locks(m, "0.9.0")
    assert set(locks) == {"a", "c"}  # b needs >=1.0.0; c is unbounded
    assert locks["a"] == "ra"
    assert "safety advisory" in locks["c"]  # empty reason gets a default
    assert active_feature_locks(m, "1.0.0") == {"b": "rb", "c": locks["c"]}


# --- extract_portable_update ---------------------------------------------- #


def test_extract_portable_update_writes_files(tmp_path) -> None:
    import zipfile

    from quill.core.updates import extract_portable_update

    zip_path = tmp_path / "quill-portable.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("quill.exe", "fake exe bytes")
        zf.writestr("data/README.txt", "placeholder")

    dest = tmp_path / "extracted"
    extract_portable_update(zip_path, dest)

    assert (dest / "quill.exe").read_text() == "fake exe bytes"
    assert (dest / "data" / "README.txt").read_text() == "placeholder"


def test_extract_portable_update_creates_dest_dir(tmp_path) -> None:
    import zipfile

    from quill.core.updates import extract_portable_update

    zip_path = tmp_path / "quill-portable.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("quill.exe", "x")

    dest = tmp_path / "nested" / "extracted"
    extract_portable_update(zip_path, dest)

    assert dest.is_dir()
    assert (dest / "quill.exe").is_file()


def test_extract_portable_update_rejects_zip_slip(tmp_path) -> None:
    import zipfile

    import pytest

    from quill.core.updates import extract_portable_update

    zip_path = tmp_path / "malicious.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../../evil.txt", "escaped")

    dest = tmp_path / "extracted"
    with pytest.raises(ValueError, match="unsafe archive entry"):
        extract_portable_update(zip_path, dest)


def test_extract_portable_update_rejects_decompression_bomb(tmp_path) -> None:
    import zipfile

    import pytest

    from quill.core.safe_archive import DecompressionBombError
    from quill.core.updates import extract_portable_update

    zip_path = tmp_path / "bomb.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("big.txt", "x" * 1000)

    dest = tmp_path / "extracted"
    with pytest.raises(DecompressionBombError):
        extract_portable_update(zip_path, dest, max_total=10)
