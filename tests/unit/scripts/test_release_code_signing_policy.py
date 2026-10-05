"""Beta and Dev builds are never code-signed; Stable always is (owner decision 2026-10-04).

The rule lives in one helper, ``scripts/code_signing.py`` (``build_decision``,
``signing_refused``), which every build asks: each ``build_release.ps1``
through ``Resolve-QuillSigning`` in ``scripts/BuildEnv.ps1``, and
``build_windows_distribution.py`` directly. These tests pin the rule per
version form, the backstops that stop ``QUILL_SIGN_REQUIRED`` / ``--require``
forcing a signature, the wiring in every PowerShell build, and the publish and
promotion checks that keep an unsigned build off Stable. Nothing here signs or
runs signtool: the toolchain and ``gh`` are fakes.
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts import build_windows_distribution as bwd
from scripts import code_signing as cs

REPO = Path(__file__).resolve().parents[3]
BUILD_SCRIPTS = sorted((REPO / "standalone").glob("*/scripts/build_release.ps1"))


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("QUILL_SIGN", "QUILL_SIGN_REQUIRED", cs.VERSION_ENV, cs.DEV_ENV):
        monkeypatch.delenv(var, raising=False)


# -- the rule, per version form ---------------------------------------------------

FINAL = ["3.2.0", "3.2.0+2", "3.2.0-build.2", "1.0.0", "3.13.20260818"]
NEVER = [
    "3.3.0-beta.2",
    "1.1.0-beta.1.build.3",
    "1.0.0-rc.1",
    "3.3.0-alpha.1",
    "3.3.0-dev.20261003.2",
    "1.0.0.dev5",
    "1.0.0 Beta 1",
    "1.0.0 Release Candidate 2",
    "1.0.0 Dev",
    "3.13.20260818-beta",
    "not a version",
    "",
]


@pytest.mark.parametrize("version", FINAL)
def test_a_final_numbered_build_may_be_signed(version: str) -> None:
    assert cs.version_may_be_signed(version)
    assert not cs.version_may_be_signed(version, dev=True)  # a Dev build never is


@pytest.mark.parametrize("version", NEVER)
def test_beta_rc_alpha_and_dev_versions_are_never_signed(version: str) -> None:
    assert not cs.version_may_be_signed(version)


@pytest.mark.parametrize("version", ["3.3.0-beta.1", "1.0.0-rc.1", "3.3.0-dev.1"])
def test_requested_and_required_cannot_force_a_prerelease(
    version: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QUILL_SIGN", "1")
    monkeypatch.setenv("QUILL_SIGN_REQUIRED", "1")
    said: list[str] = []
    assert cs.build_decision(version, out=said.append) is False
    assert said == ["Beta and Dev builds are not code-signed; signing skipped."]


def test_a_dev_build_is_refused_whatever_its_number(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUILL_SIGN", "1")
    said: list[str] = []
    assert cs.build_decision("3.3.0", dev=True, out=said.append) is False
    assert said == [cs.UNSIGNED_BUILD_MESSAGE]


def test_a_final_numbered_build_signs_exactly_as_before(monkeypatch: pytest.MonkeyPatch) -> None:
    said: list[str] = []
    assert cs.build_decision("3.2.0", out=said.append) is False  # not asked to sign
    monkeypatch.setenv("QUILL_SIGN", "1")
    assert cs.build_decision("3.2.0+2", out=said.append) is True
    assert said == []


def test_the_cli_decision_prints_one_line_then_skip(capsys: pytest.CaptureFixture[str]) -> None:
    assert cs.main(["build-decision", "--version", "3.3.0-beta.1"]) == 0
    assert capsys.readouterr().out.splitlines() == [cs.UNSIGNED_BUILD_MESSAGE, "skip"]


# -- the backstops: nothing later in a Beta build can sign ----------------------------


def _toolchain_must_not_be_touched(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(**_kwargs: object) -> cs.SigningConfig:
        raise AssertionError("a Beta or Dev build reached the signing toolchain")

    monkeypatch.setattr(cs, "resolve_config", boom)


def test_sign_paths_refuses_a_prerelease_even_when_required(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _toolchain_must_not_be_touched(monkeypatch)
    monkeypatch.setenv("QUILL_SIGN", "1")
    monkeypatch.setenv("QUILL_SIGN_REQUIRED", "1")
    target = tmp_path / "app.exe"
    target.write_bytes(b"MZ")
    assert cs.sign_paths([target], version="3.3.0-beta.1", require=True) == []
    assert cs.sign_paths([target], version="3.3.0", dev=True, require=True) == []


def test_the_version_a_build_declared_is_honoured_by_every_later_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _toolchain_must_not_be_touched(monkeypatch)
    monkeypatch.setenv("QUILL_SIGN", "1")
    monkeypatch.setenv(cs.VERSION_ENV, "3.3.0-rc.1")
    target = tmp_path / "app.exe"
    target.write_bytes(b"MZ")
    assert cs.main(["sign-build", str(target), "--require"]) == 0
    # The `sign` command Inno runs for Setup.exe fails the compile instead.
    assert cs.main(["sign", str(target)]) == 1
    assert cs.main(["sign-tree", str(tmp_path)]) == 1


def test_a_declared_final_version_does_not_block_signing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(cs.VERSION_ENV, "3.2.0+2")
    assert not cs.signing_refused()
    monkeypatch.setenv(cs.DEV_ENV, "1")
    assert cs.signing_refused()


def test_the_python_build_never_passes_inno_sign_for_a_prerelease(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QUILL_SIGN", "1")
    monkeypatch.setenv("QUILL_SIGN_REQUIRED", "1")
    assert bwd._inno_sign_args("1.0.0 Beta 1") == []
    assert bwd._inno_sign_args("1.0.0 Release Candidate 2") == []
    assert bwd._inno_sign_args("1.0.0 Dev") == []
    assert bwd._inno_sign_args("1.0.0")[0] == "/DSign"


# -- every PowerShell build asks the helper, before it signs anything --------------


def test_every_build_release_script_decides_before_it_signs() -> None:
    assert len(BUILD_SCRIPTS) >= 9
    for script in BUILD_SCRIPTS:
        text = script.read_text(encoding="utf-8")
        name = script.parent.parent.name
        decide = text.find("Resolve-QuillSigning")
        assert decide != -1, f"{name}: never asks Resolve-QuillSigning"
        assert text.find("Resolve-QuillReleaseBuild -QuillRepo") < decide, name
        assert decide < text.find("$signer sign-build"), f"{name}: signs before deciding"
        assert decide < text.find("$innoSign = @()"), f"{name}: Inno args before deciding"
        # /DSign is only ever passed when QUILL_SIGN survived the decision.
        assert re.search(r'if \(\$env:QUILL_SIGN -eq "1"\) \{\s*\$innoSign = @\("/DSign"', text)
        if "$DevVersion" in text:
            assert re.search(r"Resolve-QuillSigning [^\n]*-Dev:\(\[bool\]\$DevVersion\)", text), (
                f"{name}: a Dev build must say it is one"
            )


def test_the_runtime_installer_decides_too() -> None:
    text = (REPO / "standalone" / "runtime" / "build_runtime_installer.ps1").read_text("utf-8")
    decide = text.find("Resolve-QuillSigning")
    assert -1 < decide < text.find("$signer sign-build")
    assert '"$version-beta"' in text  # the Beta runtime slot is a Beta build


def test_resolve_quill_signing_asks_the_helper_and_clears_both_switches() -> None:
    text = (REPO / "scripts" / "BuildEnv.ps1").read_text(encoding="utf-8-sig")
    body = text[text.index("function Resolve-QuillSigning") :]
    assert '"build-decision"' in body
    assert '$env:QUILL_SIGN = ""' in body and '$env:QUILL_SIGN_REQUIRED = ""' in body
    assert "$env:QUILL_SIGN_VERSION = $Version" in body


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="PowerShell 7 is not installed")
@pytest.mark.parametrize(
    ("version", "dev", "signs"),
    [("3.3.0-beta.1", False, False), ("3.3.0", True, False), ("3.3.0", False, True)],
)
def test_the_powershell_decision_end_to_end(version: str, dev: bool, signs: bool) -> None:
    flag = " -Dev" if dev else ""
    command = (
        f". '{REPO / 'scripts' / 'BuildEnv.ps1'}'; "
        '$env:QUILL_SIGN = "1"; $env:QUILL_SIGN_REQUIRED = "1"; '
        f"$r = Resolve-QuillSigning -QuillRepo '{REPO}' -Python '{sys.executable}' "
        f"-Version '{version}'{flag}; "
        'Write-Output "result=$r sign=[$env:QUILL_SIGN] required=[$env:QUILL_SIGN_REQUIRED]"'
    )
    done = subprocess.run(  # noqa: S603 - fixed program, argument list
        ["pwsh", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    last = done.stdout.strip().splitlines()[-1]
    if signs:
        assert last == "result=True sign=[1] required=[1]"
    else:
        assert cs.UNSIGNED_BUILD_MESSAGE in done.stdout
        assert last == "result=False sign=[] required=[]"


# -- is a released file signed? -------------------------------------------------------


def _pe(*, signed: bool) -> bytes:
    data = bytearray(0x400)
    data[0:2] = b"MZ"
    data[0x3C:0x40] = (0x80).to_bytes(4, "little")
    data[0x80:0x84] = b"PE\x00\x00"
    opt = 0x80 + 24
    data[opt : opt + 2] = (0x20B).to_bytes(2, "little")
    if signed:
        cert = opt + 112 + 4 * 8
        data[cert : cert + 4] = (0x300).to_bytes(4, "little")
        data[cert + 4 : cert + 8] = (0x100).to_bytes(4, "little")
        data[0x300:0x304] = (0x100).to_bytes(4, "little")
        data[0x304:0x306] = (0x0200).to_bytes(2, "little")
        data[0x306:0x308] = (0x0002).to_bytes(2, "little")
    return bytes(data)


def test_an_embedded_signature_is_found_structurally() -> None:
    assert cs.has_embedded_signature(_pe(signed=True))
    assert not cs.has_embedded_signature(_pe(signed=False))
    assert not cs.has_embedded_signature(b"installer bytes")
    assert not cs.has_embedded_signature(_pe(signed=True)[:0x380])  # cut off: points past EOF


def test_a_portable_zip_is_signed_only_when_every_program_is(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def zipped(name: str, members: dict[str, bytes]) -> Path:
        path = tmp_path / name
        with zipfile.ZipFile(path, "w") as archive:
            for member, data in members.items():
                archive.writestr(member, data)
        return path

    good = zipped("good.zip", {"app.exe": _pe(signed=True), "readme.txt": b"x"})
    mixed = zipped("mixed.zip", {"app.exe": _pe(signed=True), "helper.exe": _pe(signed=False)})
    empty = zipped("empty.zip", {"readme.txt": b"x"})
    assert cs.asset_is_signed(good)
    assert not cs.asset_is_signed(mixed)
    assert not cs.asset_is_signed(empty)
    monkeypatch.setattr(cs, "find_signtool", lambda: None)  # the Linux promote runner
    exe = tmp_path / "Setup.exe"
    exe.write_bytes(_pe(signed=True))
    assert cs.asset_is_signed(exe)
    exe.write_bytes(_pe(signed=False))
    assert not cs.asset_is_signed(exe)


# -- publish and promotion: Stable is never unsigned -----------------------------------


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


T0 = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


class FakeGh:
    """``gh``, answering from memory: the files a release holds, and nothing else."""

    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files
        self.calls: list[list[str]] = []

    def __call__(self, args):
        args = list(args)
        self.calls.append(args)
        if args[0] == "api":
            return json.dumps([])
        if args[:2] == ["release", "download"]:
            folder = Path(args[args.index("--dir") + 1])
            for name, data in self.files.items():
                (folder / name).write_bytes(data)
            return ""
        if args[:2] == ["release", "view"]:
            return json.dumps({"isDraft": False, "tagName": args[2]})
        return ""


def _dist(tmp_path: Path, version: str) -> Path:
    dist = tmp_path / "dist"
    dist.mkdir(parents=True)
    (dist / f"Quill-Radio-Setup-Shared-{version}.exe").write_bytes(b"installer")
    return dist


def _publish(tmp_path: Path, version: str, signed: bool) -> tuple[int, list[str], list]:
    gh = FakeGh({})
    out: list[str] = []
    code = _load("publish_release").run(
        ["--app", "radio", "--version", version, "--channel", "beta"]
        + ["--dist", str(_dist(tmp_path, version)), "--no-sign"],
        gh=gh,
        root=tmp_path,
        now=T0,
        seed_reader=lambda _p: b"",
        out=out.append,
        authenticode=lambda _p: signed,
    )
    return code, out, gh.calls


def test_publish_refuses_an_unsigned_stable_candidate(tmp_path: Path) -> None:
    code, out, calls = _publish(tmp_path, "3.3.0", signed=False)
    assert code == 1
    assert any(line.startswith("Refused:") and "Stable candidate" in line for line in out)
    assert not any(c[:2] == ["release", "create"] for c in calls)  # nothing was created


def test_publish_refuses_a_signed_beta(tmp_path: Path) -> None:
    code, out, calls = _publish(tmp_path, "3.3.0-beta.1", signed=True)
    assert code == 1
    assert any("never code-signed" in line for line in out)
    assert not any(c[:2] == ["release", "create"] for c in calls)


def test_publish_lists_an_unsigned_beta_and_a_signed_candidate(tmp_path: Path) -> None:
    assert _publish(tmp_path / "a", "3.3.0-beta.1", signed=False)[0] == 0
    assert _publish(tmp_path / "b", "3.3.0", signed=True)[0] == 0


def test_promotion_to_stable_always_checks_the_signature(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.tools import release_feed as rf

    version = "3.3.0"
    files = {f"Quill-Radio-Setup-Shared-{version}.exe": b"installer"}
    dist = tmp_path / "dist"
    dist.mkdir()
    for name, data in files.items():
        (dist / name).write_bytes(data)
    gh = FakeGh(files)
    publish = _load("publish_release")
    argv = ["--app", "radio", "--version", version, "--channel", "beta", "--dist", str(dist)]
    common = dict(gh=gh, root=tmp_path, seed_reader=lambda _p: b"", out=lambda _s: None)
    assert publish.run([*argv, "--no-sign"], now=T0, authenticode=lambda _p: True, **common) == 0
    monkeypatch.setattr(rf, "feed_signature_ok", lambda path, keys=None: True)
    promote = _load("promote_release")
    args = ["--app", "radio", "--version", "3.3.0+1", "--to", "stable", "--dry-run"]
    for signed, mark in ((False, "FAIL P5"), (True, "PASS P5")):
        out: list[str] = []
        promote.run(
            args,
            gh=gh,
            root=tmp_path,
            now=T0 + timedelta(days=8),
            docs_gate=lambda: True,
            out=out.append,
            authenticode=lambda _p, s=signed: s,
        )
        line = next(x for x in out if " P5 " in x)
        assert line.startswith(mark), line
        if not signed:
            assert "Stable is never unsigned" in line and "-Sign" in line
    # Without QUILL_SIGN_REQUIRED in the environment: the check is not optional.
    assert "QUILL_SIGN_REQUIRED" not in (REPO / "scripts" / "promote_release.py").read_text("utf-8")
