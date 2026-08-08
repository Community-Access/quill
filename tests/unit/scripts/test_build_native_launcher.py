"""The native-launcher build wrapper.

The compile itself needs MSVC and is exercised by actually running the script on
a build machine; these cover the parts that are wrong silently -- the identity
compiled into each executable, and the toolchain-missing contract the
per-product builds depend on.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.build_native_launcher import (
    PRODUCTS,
    LauncherToolchainMissing,
    build_launcher,
    main,
    product_icon,
    product_version,
)


def test_every_product_has_a_distinct_executable_name() -> None:
    """The exe basename is what the Inno installer copies by literal path.

    Two products sharing a name would silently overwrite each other in a build
    that stages more than one.
    """
    names = [p.name for p in PRODUCTS.values()]
    assert len(names) == len(set(names)), f"duplicate launcher names: {names}"


def test_radio_identity_matches_what_the_installer_expects() -> None:
    """quill-radio.iss copies ..\\dist\\QuillRadio\\QuillRadio.exe by literal path."""
    radio = PRODUCTS["radio"]
    assert radio.name == "QuillRadio"
    assert radio.module == "quill.apps.radio"
    assert radio.app_id == "CommunityAccess.QuillRadio"


def test_main_quill_launcher_is_named_for_portable_detection() -> None:
    """storage_mode's portable detection looks for quill.exe at the bundle root."""
    assert PRODUCTS["quill"].name == "quill"


@pytest.mark.parametrize("key", sorted(PRODUCTS))
def test_version_is_dotted_and_never_empty(key: str) -> None:
    """A blank version would produce a malformed VERSIONINFO resource.

    CMake splits this string on "." into FILEVERSION's four WORDs, so a
    non-numeric or empty value breaks the resource compile rather than the app.
    """
    version = product_version(PRODUCTS[key])
    assert version, f"{key} resolved an empty version"
    assert version[0].isdigit(), f"{key} version {version!r} is not dotted-numeric"


@pytest.mark.parametrize("key", sorted(PRODUCTS))
def test_declared_icons_exist(key: str) -> None:
    """A product that names an icon must actually ship it.

    CMake silently drops a missing -DPRODUCT_ICON, so a typo would produce an
    iconless exe and no error anywhere.
    """
    product = PRODUCTS[key]
    if not product.icon_dir:
        return
    assert product_icon(product) is not None, (
        f"{key} declares {product.icon_name}.ico under standalone/{product.icon_dir}/assets "
        "but it is not there"
    )


def test_missing_toolchain_is_reported_not_raised(monkeypatch, tmp_path: Path, capsys) -> None:
    """Best-effort by design: exit 0, produce nothing, say why.

    The per-product build scripts check for the exe themselves and treat its
    absence as fatal, so this stays usable on a dev machine with no C toolchain
    while a release build still cannot silently ship without a launcher.
    """
    monkeypatch.setattr("scripts.build_native_launcher.find_cmake", lambda: None)
    assert main(["--product", "radio", "--out", str(tmp_path)]) == 0
    assert not list(tmp_path.glob("*.exe"))
    assert "cmake" in capsys.readouterr().err.lower()


def test_require_toolchain_makes_it_fatal(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("scripts.build_native_launcher.find_cmake", lambda: None)
    assert main(["--product", "radio", "--out", str(tmp_path), "--require-toolchain"]) == 1


def test_build_launcher_raises_when_msvc_is_absent(monkeypatch, tmp_path: Path) -> None:
    """CMake alone is not enough -- MSVC is what compiles the C."""
    monkeypatch.setattr("scripts.build_native_launcher.find_cmake", lambda: "cmake")
    monkeypatch.setattr("scripts.build_native_launcher.find_msvc", lambda: None)
    with pytest.raises(LauncherToolchainMissing, match="Visual Studio"):
        build_launcher(PRODUCTS["radio"], tmp_path)
