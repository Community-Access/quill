"""Release-channel rehearsal against a real feed server (plan 10.1, Rehearsal).

Publishes on Dev, promotes to Beta and then Stable, publishes the next Beta,
withdraws it and goes back to Stable, with the real scripts and a fake
``gh`` -- and the app fetching each list over HTTPS from
``QUILL_UPDATE_FEED_BASE``, exactly as an installed copy does (signature,
trusted hosts, sequence high-water mark, expiry).

Opt in. It needs a throwaway place that serves files over HTTPS on a trusted
host (add it to ``QUILL_UPDATE_TRUSTED_HOSTS`` if it is not GitHub's), and the
folder on this computer that it serves::

    $env:QUILL_CHANNEL_REHEARSAL = "1"
    $env:QUILL_UPDATE_FEED_BASE = "https://rehearsal.example/updates/v2/"
    $env:QUILL_REHEARSAL_SERVE_DIR = "D:/rehearsal/updates/v2"
    pytest tests/integration/test_channel_rehearsal.py -v

Nothing here touches the real feeds, the owner's key or GitHub. The offline
twin, ``tests/unit/scripts/test_channel_rehearsal_offline.py``, runs in CI.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("QUILL_CHANNEL_REHEARSAL") != "1"
    or not os.environ.get("QUILL_UPDATE_FEED_BASE")
    or not os.environ.get("QUILL_REHEARSAL_SERVE_DIR"),
    reason=(
        "Live release-channel rehearsal; set QUILL_CHANNEL_REHEARSAL=1, "
        "QUILL_UPDATE_FEED_BASE and QUILL_REHEARSAL_SERVE_DIR to run."
    ),
)


def _flow():
    path = Path(__file__).resolve().with_name("channel_rehearsal_flow.py")
    spec = importlib.util.spec_from_file_location("channel_rehearsal_flow", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def test_channel_rehearsal_over_https(tmp_path: Path, monkeypatch) -> None:
    pytest.importorskip("nacl")
    from nacl.signing import SigningKey

    serve = Path(os.environ["QUILL_REHEARSAL_SERVE_DIR"])
    serve.mkdir(parents=True, exist_ok=True)

    def deploy(folder: Path) -> None:
        for path in folder.iterdir():
            if path.suffix in (".json", ".sig"):
                shutil.copyfile(path, serve / path.name)

    key = SigningKey.generate()
    seen = _flow().rehearse(
        tmp_path / "repo",
        seed=bytes(key),
        keys=[bytes(key.verify_key)],
        state_dir=tmp_path / "state",
        monkeypatch=monkeypatch,
        get=None,
        deploy=deploy,
    )
    assert seen["stable"].current("stable").version == "3.3.0"
    assert seen["revoked"].current("beta").version == "3.3.0"
    assert seen["target"].version == "3.3.0"
