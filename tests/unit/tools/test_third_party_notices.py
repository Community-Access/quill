"""GATE-NOTICES: the family's third-party notices are generated, complete and shipped.

One catalogue (``quill/data/third_party/components.json``) renders every
notices file: the family document in ``docs/legal`` and each installer app's
``THIRD-PARTY-NOTICES.txt`` and ``LICENSE.txt``. These tests hold the rendered
files to the catalogue, the catalogue to the build inventories, the installers
to the files, and Help > About to the files it opens.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core import third_party_notices as tpn
from quill.tools import build_third_party_notices as build
from quill.ui import about_notices

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def catalogue() -> tpn.Catalogue:
    return tpn.load_catalogue()


def test_every_rendered_notices_file_matches_the_catalogue(catalogue) -> None:
    for path, text in build.outputs(catalogue).items():
        committed = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        assert committed == text, (
            f"{path.relative_to(ROOT)} has drifted from the catalogue. Regenerate with: "
            "python -m quill.tools.build_third_party_notices --write"
        )


def test_every_python_distribution_in_a_build_inventory_has_an_entry(catalogue) -> None:
    missing = build.uncatalogued(catalogue)
    assert not missing, "No catalogue entry for:\n" + "\n".join(missing)


def test_every_cited_licence_text_exists(catalogue) -> None:
    for key in catalogue.licenses:
        meta = catalogue.licenses[key]
        if meta.get("text"):
            assert catalogue.license_text(key), key
        else:
            assert meta.get("url") or key in ("Public-Domain", "Unknown"), (
                f"{key} has neither a bundled text nor a URL"
            )


def test_each_licence_text_appears_once_in_the_family_document(catalogue) -> None:
    text = tpn.render_markdown(catalogue)
    for key in tpn._used_licenses(catalogue.components):
        name = catalogue.licenses[key]["name"]
        assert text.count(f"### {name}\n") == 1, name


def test_ffmpeg_entry_names_its_version_licence_and_source(catalogue) -> None:
    from quill.core.speech.ffmpeg_install import FFMPEG_PINNED_VERSION

    ffmpeg = next(item for item in catalogue.components if item.id == "ffmpeg")
    assert FFMPEG_PINNED_VERSION in ffmpeg.version
    assert "GPL-3.0-or-later" in ffmpeg.license_label
    assert "ffmpeg.org/releases" in ffmpeg.obligations


def test_shipped_files_carry_no_maintainer_review_notes(catalogue) -> None:
    for key, meta in catalogue.products.items():
        if meta.get("standalone"):
            text = tpn.render_text(catalogue, key)
            assert "Needs review" not in text, key
    assert "Needs review" in tpn.render_markdown(catalogue)


def test_build_only_components_stay_out_of_the_product_files(catalogue) -> None:
    text = tpn.render_text(catalogue, "radio")
    assert "Inno Setup" not in text
    assert "Quill Radio: Third-Party Notices" in text


@pytest.mark.parametrize("iss", sorted((ROOT / "standalone").glob("*/installer/*.iss")))
def test_every_app_installer_installs_its_notices_and_licence(iss: Path) -> None:
    text = iss.read_text(encoding="utf-8-sig")
    for name in ("THIRD-PARTY-NOTICES.txt", "LICENSE.txt"):
        line = next(
            (ln for ln in text.splitlines() if f'Source: "..\\{name}"' in ln),
            None,
        )
        assert line is not None, f"{iss.relative_to(ROOT)} does not install {name}"
        assert "skipifsourcedoesntexist" not in line


def test_the_portable_builder_stages_the_notices() -> None:
    source = (ROOT / "standalone" / "studio" / "scripts" / "build_portable.py").read_text(
        encoding="utf-8"
    )
    assert "_stage_notices(out_dir, product, source_root)" in source


# -- Help > About -----------------------------------------------------------


def test_about_finds_the_file_beside_the_program_first(tmp_path: Path) -> None:
    beside = tmp_path / about_notices.NOTICES_FILE
    beside.write_text("notices", encoding="utf-8")
    assert about_notices.find_notices("radio", folders=[tmp_path]) == beside


def test_about_falls_back_to_the_checkout_then_the_family_document(tmp_path: Path) -> None:
    found = about_notices.find_notices("radio", folders=[tmp_path])
    assert found == ROOT / "standalone" / "radio" / "THIRD-PARTY-NOTICES.txt"
    # Quill Media Player has no installer and no file of its own.
    player = about_notices.find_notices("player", folders=[tmp_path])
    assert player == ROOT / "docs" / "legal" / "THIRD_PARTY_NOTICES.txt"


def test_opening_the_notices_speaks_the_outcome(tmp_path: Path) -> None:
    said: list[str] = []
    opened: list[str] = []

    def fake_open(url: str) -> bool:
        opened.append(url)
        return True

    assert about_notices.open_notices(
        "radio", "Quill Radio", said.append, folders=[tmp_path], open_url=fake_open
    )
    assert opened and opened[0].startswith("file:")
    assert said == ["Opened the licences and notices for Quill Radio."]


def test_a_build_without_notices_says_so(monkeypatch, tmp_path: Path) -> None:
    said: list[str] = []
    monkeypatch.setattr(about_notices, "notices_candidates", lambda app, folders=None: [])
    assert not about_notices.open_notices("radio", "Quill Radio", said.append)
    assert said == ["The licences and notices for Quill Radio were not found in this build."]


def test_quill_prefers_the_generated_file_to_rendering_metadata(tmp_path: Path) -> None:
    legal = tmp_path / "docs" / "legal"
    legal.mkdir(parents=True)
    (legal / "THIRD-PARTY-NOTICES-QUILL.txt").write_text("GENERATED", encoding="utf-8")
    text = about_notices.quill_notices_text(tmp_path, tmp_path / "pyproject.toml")
    assert text == "GENERATED"
    empty = tmp_path / "elsewhere"
    empty.mkdir()
    fallback = about_notices.quill_notices_text(empty, empty / "pyproject.toml")
    assert "not available in this build" in fallback


def test_about_button_access_key_is_unique_in_the_window() -> None:
    assert about_notices.NOTICES_BUTTON_LABEL.count("&") == 1
    assert "&L" in about_notices.NOTICES_BUTTON_LABEL
