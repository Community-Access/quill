"""Every release carries its licence, notices and copyleft source manifest.

publish_release.py uploads ``LICENSE.txt``, ``THIRD-PARTY-NOTICES.txt`` and
``copyleft-sources.json``/``.txt`` beside the binaries of every release it
creates, and adds whichever of them an existing release lacks -- without
downloading anything. These drive it with a fake ``gh`` against a temp feed.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
T0 = datetime(2026, 11, 1, tzinfo=UTC)
VERSION = "3.3.0-beta.1"
FILES = {
    f"Quill-Radio-Setup-Shared-{VERSION}.exe": b"installer bytes",
    f"Quill-Radio-Portable-{VERSION}.zip": b"portable bytes",
}


def _load():
    spec = importlib.util.spec_from_file_location(
        "publish_release", REPO / "scripts" / "publish_release.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["publish_release"] = module
    spec.loader.exec_module(module)
    return module


class FakeGh:
    def __init__(self, on_release: dict[str, bytes]) -> None:
        self.on_release = on_release
        self.calls: list[list[str]] = []

    def __call__(self, args):
        args = list(args)
        self.calls.append(args)
        if args[0] == "api":
            return json.dumps([])
        if args[:2] == ["release", "download"]:
            folder = Path(args[args.index("--dir") + 1])
            for name, data in self.on_release.items():
                (folder / name).write_bytes(data)
        return ""


def _run(publish, argv, gh, tmp_path):
    out: list[str] = []
    code = publish.run(
        [*argv, "--no-sign", "--build", "1"],
        gh=gh,
        root=tmp_path,
        now=T0,
        seed_reader=lambda _p: b"",
        out=out.append,
        authenticode=lambda _p: False,
    )
    return code, out


def _dist(tmp_path: Path) -> Path:
    dist = tmp_path / "dist"
    dist.mkdir()
    for name, data in FILES.items():
        (dist / name).write_bytes(data)
    return dist


def test_a_new_release_uploads_the_licence_files_beside_the_binaries(tmp_path: Path) -> None:
    publish = _load()
    dist = _dist(tmp_path)
    gh = FakeGh(FILES)

    code, out = _run(
        publish,
        ["--app", "radio", "--version", VERSION, "--channel", "beta", "--dist", str(dist)],
        gh,
        tmp_path,
    )

    assert code == 0, out
    create = next(c for c in gh.calls if c[:2] == ["release", "create"])
    uploaded = {Path(arg).name for arg in create if Path(arg).parent == dist}
    assert set(publish.COMPLIANCE_NAMES) <= uploaded
    licence = (dist / "LICENSE.txt").read_bytes()
    assert licence == (REPO / "standalone" / "radio" / "LICENSE.txt").read_bytes()
    manifest = json.loads((dist / "copyleft-sources.json").read_text(encoding="utf-8"))
    assert manifest["product"] == "radio"
    assert any(c["id"] == "mutagen" for c in manifest["components"])


def test_a_manifest_the_build_wrote_is_kept(tmp_path: Path) -> None:
    publish = _load()
    dist = _dist(tmp_path)
    (dist / "copyleft-sources.json").write_text('{"from": "the build"}\n', encoding="utf-8")
    (dist / "copyleft-sources.txt").write_text("from the build\n", encoding="utf-8")

    code, out = _run(
        publish,
        ["--app", "radio", "--version", VERSION, "--channel", "beta", "--dist", str(dist)],
        FakeGh(FILES),
        tmp_path,
    )

    assert code == 0, out
    assert json.loads((dist / "copyleft-sources.json").read_text(encoding="utf-8")) == {
        "from": "the build"
    }


def test_a_dry_run_writes_and_uploads_nothing(tmp_path: Path) -> None:
    publish = _load()
    dist = _dist(tmp_path)
    gh = FakeGh(FILES)

    code, out = _run(
        publish,
        [
            "--app",
            "radio",
            "--version",
            VERSION,
            "--channel",
            "beta",
            "--dist",
            str(dist),
            "--dry-run",
        ],
        gh,
        tmp_path,
    )

    assert code == 0, out
    assert not (dist / "LICENSE.txt").exists()
    assert not any(c[:2] in (["release", "create"], ["release", "upload"]) for c in gh.calls)
    assert any(line.startswith("Licence files: would add") for line in out)


def test_an_existing_release_gets_the_files_it_lacks(tmp_path: Path) -> None:
    publish = _load()
    gh = FakeGh({**FILES, "LICENSE.txt": b"already there"})

    code, out = _run(
        publish,
        ["--app", "radio", "--version", VERSION, "--channel", "beta", "--existing"],
        gh,
        tmp_path,
    )

    assert code == 0, out
    upload = next(c for c in gh.calls if c[:2] == ["release", "upload"])
    names = {Path(arg).name for arg in upload[3:] if not arg.startswith("--")}
    assert {"THIRD-PARTY-NOTICES.txt", "copyleft-sources.json", "copyleft-sources.txt"} <= names
    assert "LICENSE.txt" not in names


def test_an_existing_release_with_every_file_is_left_alone(tmp_path: Path) -> None:
    publish = _load()
    complete = {**FILES, **{name: b"x" for name in publish.COMPLIANCE_NAMES}}
    gh = FakeGh(complete)

    code, out = _run(
        publish,
        ["--app", "radio", "--version", VERSION, "--channel", "beta", "--existing"],
        gh,
        tmp_path,
    )

    assert code == 0, out
    assert not any(c[:2] == ["release", "upload"] for c in gh.calls)
    assert "Licence files: already on the release." in out


def test_every_app_has_its_licence_files_committed() -> None:
    from quill.tools import release_feed as rf

    publish = _load()
    for app_key in rf.APPS:
        for name, source in publish.licence_sources(app_key).items():
            assert source.is_file(), f"{app_key}: {name} from {source}"


def test_the_family_build_puts_the_licence_files_in_every_upload_without_downloading() -> None:
    """build-quill-apps.ps1 cannot run here; pin the upload step's shape instead."""
    script = (REPO / "build-quill-apps.ps1").read_text(encoding="utf-8-sig")
    upload = script[script.index('Step "Upload zips"') :]
    assert "Get-LicenceFiles $app" in upload
    call = upload[upload.index("$sourcesCode = Invoke-Logged") :]
    call = call[: call.index(")")]
    assert r'"scripts\collect_copyleft_sources.py"' in call
    assert '"--build-dir", $runtimeDist' in call
    assert "--download" not in call
    for name in ("LICENSE.txt", "THIRD-PARTY-NOTICES.txt", "copyleft-sources.json"):
        assert name in upload


def test_the_family_build_also_zips_each_installer_on_its_own() -> None:
    """Some mail and file shares refuse a bare .exe; the upload carries a zip of it too."""
    script = (REPO / "build-quill-apps.ps1").read_text(encoding="utf-8-sig")
    upload = script[script.index('Step "Upload zips"') :]
    assert '$file.Name -like "*Setup*"' in upload
    assert "Compress-Archive -LiteralPath $file.FullName -DestinationPath $setupZip" in upload
    assert '$sums.Add("$hash  $app/$(Split-Path $setupZip -Leaf)")' in upload
