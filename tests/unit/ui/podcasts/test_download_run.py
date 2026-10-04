"""qc.md F-10: a Download All batch says its progress and ends in one sentence."""

from __future__ import annotations

from quill.core import activity
from quill.ui.podcasts import download_run


class _Host:
    def __init__(self) -> None:
        self.said: list[str] = []

    def _announce(self, message: str, **_kw: object) -> None:
        self.said.append(message)


def test_a_batch_says_quarters_and_one_result(monkeypatch) -> None:
    monkeypatch.setattr("quill.ui.quiet_hours_ui.held_back", lambda *_a, **_k: False)
    host = _Host()
    download_run.start(host, "The Daily", ["a", "b", "c", "d"], folder="C:/x")
    download_run.step(host, "a")
    download_run.step(host, "zz")  # not this batch
    download_run.step(host, "b", failed_title="Episode B")
    download_run.step(host, "c")
    download_run.step(host, "d")
    assert host.said[0] == "Downloading The Daily, 1 of 4, 25 percent"
    assert host.said[-1] == (
        "Downloaded 3 of 4 episodes of The Daily. 1 failed; Recent Problems says why."
    )
    latest = activity.LOG.latest_important()
    assert latest is not None and latest.has("open_folder")


def test_a_single_download_is_not_tallied() -> None:
    host = _Host()
    download_run.start(host, "Show", ["only"])
    assert getattr(host, "_download_run", None) is None
