"""The update-feed publisher can emit signed feature kill-switch advisories."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    "generate_update_feed", _ROOT / "scripts" / "generate_update_feed.py"
)
assert _spec and _spec.loader
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

from quill.core.updates import active_feature_locks, parse_update_manifest  # noqa: E402


def test_publisher_emits_signed_advisory_that_verifies() -> None:
    payload = gen.build_payload(
        version="0.9.0",
        download_url="https://github.com/Community-Access/quill/releases/download/latest/x.exe",
        advisories=[
            {
                "feature_id": "core.glow",
                "reason": "Investigating a crash",
                "max_version": "0.9.5",
                "advisory_id": "lock-1",
            }
        ],
    )
    assert payload["advisories"][0]["feature_id"] == "core.glow"
    # The client verifies the signature (which covers the advisory) and resolves it.
    import json

    manifest = parse_update_manifest(json.dumps(payload))
    assert active_feature_locks(manifest, "0.9.0") == {"core.glow": "Investigating a crash"}
    assert active_feature_locks(manifest, "0.9.9") == {}  # a fix past max lifts it


def test_publisher_without_advisories_omits_the_key() -> None:
    payload = gen.build_payload(
        version="0.9.0",
        download_url="https://github.com/Community-Access/quill/releases/download/latest/x.exe",
    )
    assert "advisories" not in payload  # backward-compatible feed shape
