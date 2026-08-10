from __future__ import annotations

from pathlib import Path

import pytest

from scripts.release_readiness import MINIMUM_PANDOC, _resolve_pandoc


def _fake_pandoc(tmp_path: Path, name: str, version: str) -> Path:
    """A stand-in executable whose --version output names ``version``."""
    path = tmp_path / name
    path.write_text(f"pandoc {version}\n", encoding="utf-8")
    return path


@pytest.fixture
def stub_versions(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Route version probing through a table instead of running executables."""
    table: dict[str, str] = {}

    def fake_version(executable: str) -> tuple[int, ...] | None:
        reported = table.get(str(Path(executable)))
        return tuple(int(part) for part in reported.split(".")) if reported else None

    monkeypatch.setattr("scripts.release_readiness._pandoc_version", fake_version)
    return table


def test_override_is_honoured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stub_versions: dict[str, str]
) -> None:
    chosen = _fake_pandoc(tmp_path, "pandoc.exe", "3.10.1")
    stub_versions[str(chosen)] = "3.10.1"
    monkeypatch.setenv("QUILL_PANDOC", str(chosen))
    assert _resolve_pandoc() == str(chosen)


def test_override_rejects_a_missing_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_PANDOC", str(tmp_path / "absent.exe"))
    with pytest.raises(RuntimeError, match="not a file"):
        _resolve_pandoc()


def test_override_rejects_a_version_below_the_minimum(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stub_versions: dict[str, str]
) -> None:
    old = _fake_pandoc(tmp_path, "pandoc.exe", "3.9.0.2")
    stub_versions[str(old)] = "3.9.0.2"
    monkeypatch.setenv("QUILL_PANDOC", str(old))
    with pytest.raises(RuntimeError, match="3.9.0.2"):
        _resolve_pandoc()


def test_newest_wins_over_path_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stub_versions: dict[str, str]
) -> None:
    """The regression this exists for: PATH order is not version order.

    Windows composes PATH as machine entries then user entries, so an old
    per-machine Pandoc shadows a newer per-user one and every render silently
    used the wrong binary.
    """
    monkeypatch.delenv("QUILL_PANDOC", raising=False)
    old = _fake_pandoc(tmp_path, "old.exe", "3.9.0.2")
    new = _fake_pandoc(tmp_path, "new.exe", "3.10.1")
    stub_versions[str(old)] = "3.9.0.2"
    stub_versions[str(new)] = "3.10.1"
    # PATH order deliberately puts the older copy first.
    monkeypatch.setattr(
        "scripts.release_readiness._pandoc_candidates", lambda: [str(old), str(new)]
    )
    assert _resolve_pandoc() == str(new)


def test_all_candidates_too_old_is_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stub_versions: dict[str, str]
) -> None:
    monkeypatch.delenv("QUILL_PANDOC", raising=False)
    old = _fake_pandoc(tmp_path, "old.exe", "3.9.0.2")
    stub_versions[str(old)] = "3.9.0.2"
    monkeypatch.setattr("scripts.release_readiness._pandoc_candidates", lambda: [str(old)])
    with pytest.raises(RuntimeError) as excinfo:
        _resolve_pandoc()
    # The message must name the offending copy so the fix is obvious.
    assert str(old) in str(excinfo.value)


def test_no_pandoc_at_all_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUILL_PANDOC", raising=False)
    monkeypatch.setattr("scripts.release_readiness._pandoc_candidates", list)
    with pytest.raises(RuntimeError, match="Pandoc is required"):
        _resolve_pandoc()


def test_minimum_matches_the_bundled_pandoc() -> None:
    """The floor must track MIRRORED_PANDOC_URL in build_windows_distribution.py."""
    source = Path("scripts/build_windows_distribution.py").read_text(encoding="utf-8")
    bundled = f"pandoc-{'.'.join(str(part) for part in MINIMUM_PANDOC)}-windows-x86_64.zip"
    assert bundled in source
