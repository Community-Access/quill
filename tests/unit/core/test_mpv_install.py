"""The on-demand libmpv download: the route the app did not have.

``libmpv-pack.zip`` was pinned on the ``assets-v1`` release for as long as the
build has been reproducible -- ``scripts/fetch_build_deps.py --only libmpv``
stages the very DLL the installers bundle -- while the running app told
listeners the engine was "not downloadable on its own". These cover the route,
and above all the two agreements that make it worth having: it fetches the same
pinned component the build does, and it writes where the resolver looks.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core import mpv_install
from quill.core.mpv_install import (
    COMPONENT,
    DLL_NAME,
    MpvInstallError,
    install_mpv,
    managed_mpv_dir,
    mpv_installed,
)


def test_it_fetches_the_same_pinned_component_the_build_does() -> None:
    """One pin, two consumers. A second URL or hash here could drift."""
    from quill.core.release_assets import ASSETS, is_pinned

    asset = ASSETS[COMPONENT]
    assert is_pinned(asset), "the libmpv asset must be SHA-pinned, not a placeholder"
    assert asset.expect_member == DLL_NAME
    assert asset.tag == "assets-v1"
    assert len(asset.sha256) == 64


def test_the_build_fetcher_names_the_same_component() -> None:
    import scripts.fetch_build_deps as fetch_build_deps

    assert COMPONENT in fetch_build_deps.COMPONENTS
    assert fetch_build_deps.LIBMPV_SENTINEL == DLL_NAME


def test_the_downloader_writes_where_the_resolver_looks() -> None:
    """The agreement that decides whether installing changes anything at all.

    A downloader writing to a folder ``find_libmpv`` never probes would report
    success and leave the app exactly as broken -- the worst shape a bug takes.
    """
    from quill.ui.audio.mpv_engine import mpv_pack_dir

    assert mpv_pack_dir() == managed_mpv_dir()
    assert managed_mpv_dir().name == "mpv"
    assert managed_mpv_dir().parent.name == "engine-packs"


def test_safe_mode_refuses_before_touching_the_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")

    def _explode(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Safe Mode must refuse before any download is attempted")

    monkeypatch.setattr("quill.core.release_assets.fetch_component", _explode)
    with pytest.raises(MpvInstallError, match="Safe Mode"):
        install_mpv()


def test_an_unsupported_platform_says_what_to_do_instead(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    monkeypatch.setattr(mpv_install, "mpv_install_supported", lambda: False)
    with pytest.raises(MpvInstallError) as excinfo:
        install_mpv(dest_dir=tmp_path)
    # Naming Homebrew and QUILL_LIBMPV is the difference between a refusal and
    # a dead end for the one platform this cannot serve.
    assert "brew install mpv" in str(excinfo.value)
    assert "QUILL_LIBMPV" in str(excinfo.value)


def test_a_pack_without_the_dll_is_a_failure_not_a_silent_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """fetch_component verifies the archive; this verifies what came out of it."""
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    monkeypatch.setattr(mpv_install, "mpv_install_supported", lambda: True)

    def _fetch_nothing(component: str, target_dir: Path, **_kwargs: object) -> Path:
        assert component == COMPONENT
        Path(target_dir).mkdir(parents=True, exist_ok=True)
        (Path(target_dir) / "README-SOURCE.txt").write_text("source offer", encoding="utf-8")
        return Path(target_dir)

    monkeypatch.setattr("quill.core.release_assets.fetch_component", _fetch_nothing)
    with pytest.raises(MpvInstallError, match=DLL_NAME):
        install_mpv(dest_dir=tmp_path)


def test_a_good_pack_returns_the_dll_and_reports_completion(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    monkeypatch.setattr(mpv_install, "mpv_install_supported", lambda: True)

    def _fetch(component: str, target_dir: Path, **_kwargs: object) -> Path:
        target = Path(target_dir)
        target.mkdir(parents=True, exist_ok=True)
        (target / DLL_NAME).write_bytes(b"not really a dll")
        # The GPL texts and the source offer are part of the pack, not extras:
        # the whole zip is unpacked for exactly this reason.
        (target / "README-SOURCE.txt").write_text("source offer", encoding="utf-8")
        return target

    monkeypatch.setattr("quill.core.release_assets.fetch_component", _fetch)
    seen: list[tuple[float, str]] = []
    result = install_mpv(
        lambda fraction, message: seen.append((fraction, message)), dest_dir=tmp_path
    )

    assert result == tmp_path / DLL_NAME
    assert result.is_file()
    assert (tmp_path / "README-SOURCE.txt").is_file(), "the GPL source offer must land beside it"
    assert seen and seen[-1][0] == 1.0, "the caller's progress bar must be closed out"


def test_installed_asks_about_the_managed_copy_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Narrower than find_libmpv() on purpose: this is 'is there anything to remove?'."""
    monkeypatch.setattr(mpv_install, "managed_mpv_dir", lambda: tmp_path)
    assert mpv_installed() is False
    (tmp_path / DLL_NAME).write_bytes(b"x")
    assert mpv_installed() is True
