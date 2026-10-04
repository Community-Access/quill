"""The release-channel rehearsal, entirely offline (plan 10.1, Rehearsal).

The same flow as ``tests/integration/test_channel_rehearsal.py`` -- publish
on Dev, promote to Beta and Stable, publish the next Beta, withdraw it, go
back to Stable -- but the app reads the lists straight from the feed folder
through ``QUILL_UPDATE_FEED_BASE``, so it runs in every CI build.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytest.importorskip("nacl")
from nacl.signing import SigningKey  # noqa: E402

from quill.core.updater.feed_fetch import FeedMissing  # noqa: E402
from quill.tools.release_feed import tag_for  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
BASE = "https://rehearsal.invalid/quill/updates/v2/"


def _flow():
    path = REPO / "tests" / "integration" / "channel_rehearsal_flow.py"
    spec = importlib.util.spec_from_file_location("channel_rehearsal_flow", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def test_publish_promote_withdraw_and_go_back_offline(tmp_path: Path, monkeypatch) -> None:
    flow = _flow()
    key = SigningKey.generate()
    monkeypatch.setenv("QUILL_UPDATE_FEED_BASE", BASE)
    folder = tmp_path / "repo" / "docs" / "site" / "updates" / "v2"
    asked: list[str] = []

    def get(url: str) -> bytes:
        asked.append(url)
        assert url.startswith(BASE), url
        path = folder / url[len(BASE) :]
        if not path.is_file():
            raise FeedMissing(url)
        return path.read_bytes()

    seen = flow.rehearse(
        tmp_path / "repo",
        seed=bytes(key),
        keys=[bytes(key.verify_key)],
        state_dir=tmp_path / "state",
        monkeypatch=monkeypatch,
        get=get,
        deploy=lambda _folder: None,
    )

    assert asked and all(url.startswith(BASE) for url in asked)
    assert seen["dev"].current("dev").version == "3.3.0"
    assert seen["dev"].current("beta") is None
    assert seen["beta"].current("beta").version == "3.3.0"
    stable = seen["stable"]
    assert stable.current("stable").version == "3.3.0"
    assert stable.sequence > seen["beta"].sequence > seen["dev"].sequence
    summary = stable.release("3.3.0").notes_summary
    assert "What's new since 3.2.0" in summary
    assert "Website button" in summary and "station name" in summary
    assert "Beta 1 brought in" not in summary and "empty favorites" not in summary
    assert "None known" not in summary
    assert any("What's new since 3.2.0" in line for line in seen["dry_run"])
    edit = next(c for c in seen["gh"].calls if c[:2] == ["release", "edit"] and "--notes" in c)
    assert "What's new since 3.2.0" in edit[edit.index("--notes") + 1]

    # Beta lists a release with its build; it was withdrawn by its plain number.
    assert seen["next_beta"].current("beta").version == "3.4.0-beta.1+1"
    revoked = seen["revoked"]
    assert revoked.release("3.4.0-beta.1+1").revoked
    assert revoked.current("beta").version == "3.3.0"
    assert all(not offer.version.startswith("3.4.0-beta.1") for offer in seen["offers"])
    assert seen["gh"].titles[tag_for("radio", "3.4.0-beta.1+1")].endswith("(withdrawn)")
    assert not any(c[:2] == ["release", "delete"] and "3.4.0" in c[2] for c in seen["gh"].calls)

    assessment = seen["assessment"]
    assert assessment.is_downgrade and assessment.verdict.kind == "safe"
    assert seen["target"].version == "3.3.0"


def test_a_replayed_older_list_is_refused_after_the_withdrawal(tmp_path: Path, monkeypatch) -> None:
    """The withdrawal only protects anyone if an older list cannot be served again."""
    from quill.core.updater.feed_fetch import fetch_feed

    flow = _flow()
    key = SigningKey.generate()
    monkeypatch.setenv("QUILL_UPDATE_FEED_BASE", BASE)
    folder = tmp_path / "repo" / "docs" / "site" / "updates" / "v2"
    snapshots: list[tuple[bytes, bytes]] = []

    def deploy(path: Path) -> None:
        snapshots.append((
            (path / "radio.json").read_bytes(),
            (path / "radio.json.sig").read_bytes(),
        ))

    def get(url: str) -> bytes:
        path = folder / url[len(BASE) :]
        return path.read_bytes()

    state = tmp_path / "state"
    flow.rehearse(
        tmp_path / "repo",
        seed=bytes(key),
        keys=[bytes(key.verify_key)],
        state_dir=state,
        monkeypatch=monkeypatch,
        get=get,
        deploy=deploy,
    )
    before_withdrawal = snapshots[-2]

    def replay(url: str) -> bytes:
        return before_withdrawal[1] if url.endswith(".sig") else before_withdrawal[0]

    result = fetch_feed("radio", get=replay, keys=[bytes(key.verify_key)], state_dir=state)
    assert result.status == "invalid"
