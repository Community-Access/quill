from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from quill.core.shell_verbs import default_shell_verbs
from scripts.build_windows_distribution import (
    DEFAULT_BUNDLED_WHISPER_MODEL_ID,
    FASTER_WHISPER_WHEELHOUSE_REQUIREMENTS,
    KOKORO_WHEELHOUSE_REQUIREMENTS,
    MP3_WHEELHOUSE_REQUIREMENTS,
    VOSK_WHEELHOUSE_REQUIREMENTS,
    _assert_bundled_token_nonempty,
    _bundled_token_value,
    _prune_embedded_runtime,
    _speech_asset_manifest,
    _stage_pip_wheelhouse,
    _stage_whisper_model,
    build_inno_setup_script,
    build_shell_verb_registry_lines,
    build_windows_distribution,
    bundled_runtime_dependencies,
    compile_inno_setup_installer,
    find_inno_setup_compiler,
)

# build/version.toml is the local-only (gitignored) canonical release-identity
# source. The iss-sync check below re-derives product identity through it, so it
# is only meaningful when that source is present (local dev and release builds);
# CI checkouts do not have it.
_VERSION_TOML = Path(__file__).resolve().parents[3] / "build" / "version.toml"


# Builds a full portable distribution (file copies + installer-script generation),
# which can exceed the global 30s pytest-timeout on a loaded CI runner. Give this
# heavy end-to-end test more headroom; the rest of the suite keeps the default.
@pytest.mark.timeout(180)
def test_build_windows_distribution_writes_portable_and_installer_files(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "quill"
version = "2.4.6"
""".strip(),
        encoding="utf-8",
    )
    # Drive the build identity through the canonical source
    # (build/version.toml) so the test asserts the same path as production.
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "version.toml").write_text(
        'base_version = "2.4.6"\n'
        'channel = "stable"\n'
        "prerelease_number = 0\n"
        'product_name = "QUILL for All"\n'
        'publisher = "Community Access"\n',
        encoding="utf-8",
    )

    # Kokoro ships ~120 MB of model files; stage them from a local fake dir so
    # this offline test never downloads them (production downloads when no dir
    # is given). The two filenames must match _stage_kokoro's expectations.
    fake_kokoro_dir = tmp_path / "kokoro-src"
    fake_kokoro_dir.mkdir()
    (fake_kokoro_dir / "kokoro-v1.0.int8.onnx").write_text("model", encoding="utf-8")
    (fake_kokoro_dir / "voices-v1.0.bin").write_text("voices", encoding="utf-8")

    bundle = build_windows_distribution(pyproject, tmp_path / "dist", kokoro_dir=fake_kokoro_dir)

    portable_dir = tmp_path / "dist" / "portable"
    installer_script = tmp_path / "dist" / "installer" / "quill.iss"
    assert portable_dir.exists()
    # The portable bundle's entry point is quill.exe at the bundle root, and
    # the detection contract requires a sibling ``data/`` folder -- not the
    # legacy run-quill.cmd launcher.
    assert not (portable_dir / "run-quill.cmd").exists()
    assert (portable_dir / "data").is_dir()
    # The hoisted quill.exe is only written when bundle_python is True; this
    # build does not bundle Python, so we assert the absence rather than call
    # the full bundle a second time.

    readme_text = (portable_dir / "README.txt").read_text(encoding="utf-8")
    assert "QUILL for All Portable 2.4.6" in readme_text
    assert "Publisher: Community Access" in readme_text
    assert "first run" in readme_text.lower()
    assert "Pandoc Conversion Wizard" in readme_text

    assert (portable_dir / "docs" / "userguide.md").exists()
    assert not (portable_dir / "docs" / "announcement-beta.md").exists()
    assert not (portable_dir / "docs" / "QUILL-PRD.md").exists()

    manifest_path = portable_dir / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["productName"] == "QUILL for All"
    assert manifest["publisher"] == "Community Access"
    assert manifest["version"] == "2.4.6"
    assert manifest["baseVersion"] == "2.4.6"
    assert manifest["channel"] == "stable"
    assert manifest["bundledPython"] is False
    # The portable bundle's entry point is the hoisted quill.exe, not the
    # legacy run-quill.cmd launcher.
    assert manifest["portableEntry"].endswith("quill.exe")
    assert manifest.get("portableLauncher") is None
    # Nothing auto-stages any more (PRD 10.2.x footprint unbundle): Pandoc, Piper,
    # Node.js, the braille pack, whisper.cpp, Kokoro, DECtalk, and eSpeak-NG all
    # download on demand, so a default build bundles no optional tools.
    assert sorted(manifest["bundledTools"]) == []
    # manifest["docs"] is str(path.relative_to(portable_dir)), which uses the
    # BUILD HOST's os.sep -- always backslash in the real shipped product
    # (this script only ever really runs on windows-latest CI), but this test
    # also runs as a plain unit test on macOS CI, where the host is POSIX.
    assert manifest["docs"] == [str(Path("docs") / "userguide.md")]
    assert manifest["speechAssets"]["dectalk"]["downloadable"] is True
    assert manifest["speechAssets"]["espeak"]["downloadable"] is True
    assert manifest["speechAssets"]["piper"]["downloadable"] is True
    # DECtalk and eSpeak-NG are unbundled (PRD 10.2.4): not staged by default,
    # downloaded on demand from QUILL's verified assets-v1 release instead.
    assert manifest["speechAssets"]["dectalk"]["bundled"] is False
    assert (portable_dir / "tools" / "speech" / "dectalk").exists() is False
    assert manifest["speechAssets"]["espeak"]["bundled"] is False
    assert (portable_dir / "tools" / "speech" / "espeak-ng").exists() is False
    # whisper.cpp is unbundled (PRD 10.2.4): not staged by default (no --whisper-dir
    # here), downloaded on demand from QUILL's verified release asset instead.
    assert manifest["speechAssets"]["whispercpp"]["bundled"] is False
    assert (portable_dir / "tools" / "speech" / "whispercpp").exists() is False
    # Kokoro is always STAGED at the portable bundle root (kokoro-models/), the
    # location the runtime resolves a bundled copy from; the installer gates the
    # copy behind the optional speechkokoro component (asserted separately).
    assert manifest["speechAssets"]["kokoro"]["bundled"] is True
    assert (portable_dir / "kokoro-models" / "kokoro-v1.0.int8.onnx").exists()
    assert (portable_dir / "kokoro-models" / "voices-v1.0.bin").exists()

    assert installer_script.exists()
    assert bundle["installer_script"] == str(installer_script)
    assert (tmp_path / "installer" / "quill.iss").exists()
    assert bundle["reference_installer_script"] == str(tmp_path / "installer" / "quill.iss")


def test_build_inno_setup_script_mentions_portable_bundle() -> None:
    script = build_inno_setup_script("9.9.9")

    assert '#define AppName "QUILL for All"' in script
    assert '#define AppVersion "9.9.9"' in script
    assert '#define AppPublisher "Community Access"' in script
    # The portable bundle's entry point is quill.exe; run-quill.cmd is gone.
    assert '#define AppExeName "quill.exe"' in script
    assert '#define AppExeName "run-quill.cmd"' not in script
    assert 'Source: "..\\portable\\*"' in script
    # Accessibility-friendly installer flags are present.
    assert "PrivilegesRequired=lowest" in script
    assert "WizardStyle=modern" in script
    assert "DisableDirPage=no" in script
    # Installer-specific post-install info (not the portable README).
    assert "InfoAfterFile=README-installer.txt" in script
    # The amd64 embedded-Python bundle must install 64-bit only, target
    # Windows 10+, and refresh Explorer associations for the assoc tasks.
    assert "ArchitecturesAllowed=x64compatible" in script
    assert "ArchitecturesInstallIn64BitMode=x64compatible" in script
    assert "MinVersion=10.0" in script
    assert "ChangesAssociations=yes" in script
    # The dead "aiassistant" component (no [Files] payload) was removed; the
    # Writing Assistant ships with the core bundle, not as a toggle.
    assert "aiassistant" not in script
    # PRD 10.2.x footprint unbundle: NO optional components remain. Pandoc,
    # Piper, Node.js, the braille pack, whisper.cpp, Kokoro, DECtalk, and
    # eSpeak-NG all download on demand, so the installer has no [Types] or
    # [Components] section and no component/setup-type selection page at all.
    assert "\n[Types]\n" not in script
    assert "\n[Components]\n" not in script
    assert "WizardIsComponentSelected" not in script
    assert "wpSelectComponents" not in script
    assert "ShouldSkipPage" not in script
    # No component definitions or [Files] gates for any optional tool.
    for _name in (
        "pandoc",
        "speechpiper",
        "nodejs",
        "braillepack",
        "speechdectalk",
        "speechespeak",
        "speechwhisper",
        "speechkokoro",
        "speechopenvoice",
    ):
        assert f'Name: "{_name}";' not in script
        assert f"Components: {_name}" not in script
    # No per-voice DECtalk sub-components or voice-selection wizard page ever.
    assert "DecTalkVoicePage" not in script
    assert "ShouldInstallAllVoices" not in script
    assert "ShouldInstallPaulVoice" not in script
    # No [Files] Source/DestDir entries for any unbundled component.
    for _dest in (
        "{app}\\tools\\pandoc",
        "{app}\\tools\\speech\\piper",
        "{app}\\tools\\speech\\dectalk",
        "{app}\\tools\\speech\\espeak-ng",
        "{app}\\tools\\speech\\whispercpp",
        "{app}\\tools\\nodejs",
        "{app}\\vendor\\braille-pack",
        "{app}\\kokoro-models",
    ):
        assert f'DestDir: "{_dest}"' not in script
    # Node.js is no longer offered via winget at install time; the app installs
    # it on demand (quill/core/node_install.py) if a Node Quillin needs it.
    assert "OpenJS.NodeJS" not in script
    assert "winget install --id OpenJS" not in script
    # The core bundle still ships, with the optional tools excluded from it so a
    # locally staged dev copy never leaks into the installer. Checked by
    # membership (not a fixed order) since --bundle-offline reorders the same
    # always-excluded terms ahead of the optional-component terms it can lift.
    excludes_line = next(line for line in script.splitlines() if line.startswith("Source:"))
    for term in (
        "docs\\QUILL-PRD.md",
        "tools\\pandoc\\*",
        "tools\\speech\\dectalk\\*",
        "tools\\speech\\espeak-ng\\*",
        "tools\\speech\\piper\\*",
        "tools\\speech\\whispercpp\\*",
        "tools\\nodejs\\*",
        "vendor\\braille-pack\\*",
        "kokoro-models\\*",
        "_tool-download\\*",
        "_speech-download\\*",
        "*\\__pycache__\\*",
    ):
        assert term in excludes_line, f"{term!r} missing from default (non-offline) Excludes"
    assert "User Guide" in script
    assert "userguide.html" in script
    assert 'Parameters: "-m quill"' in script
    # Bundled-launcher resolution: the embedded runtime is flattened into {app},
    # so quill.exe sits next to its own python313.dll/_pth and self-runs (the
    # sitecustomize hook). BundledLauncherPath resolves {app}\quill.exe, then
    # {app}\pythonw.exe -- never a nested python\ path (the orphan that broke
    # portable launch, #722).
    assert "function BundledLauncherPath(Param: String): String;" in script
    assert "function HasBundledLauncher(): Boolean;" in script
    assert "{app}\\quill.exe" in script
    assert "{app}\\pythonw.exe" in script
    assert "{app}\\python\\quill.exe" not in script
    assert "{app}\\python\\pythonw.exe" not in script
    assert "{code:BundledLauncherPath}" in script
    assert "Check: HasBundledLauncher" in script
    assert "Check: not HasBundledLauncher" in script
    assert "UninstallDisplayIcon={code:BundledLauncherPath}" in script
    assert "Beta Announcement" not in script
    assert "Product Requirements" not in script
    # The desktop shortcut is created unconditionally. A previous (beta-1)
    # install could have left a Quill.lnk pointing at run-quill.cmd on the
    # user's desktop; the CurStepChanged(ssInstall) hook in [Code] deletes
    # that stale shortcut before the new one is created. No `desktopicon`
    # task definition should remain once the gate is removed.
    assert "Tasks: desktopicon" not in script
    assert "autodesktop" in script
    assert "{#AppName}.lnk" in script
    assert "StaleShortcut" in script
    assert "CurStep = ssInstall" in script
    # File-association registry entries use HKCU only (never overwrite defaults).
    assert "HKCU" in script
    assert "HKLM" not in script
    # The script parses as plain ASCII text (catches stray bad characters).
    script.encode("ascii")


def test_bundle_offline_lifts_optional_component_excludes() -> None:
    """--bundle-offline includes locally staged optional components in the .exe.

    Without the flag (the default/regular installer), any optional component
    staged via --pandoc-dir/--dectalk-dir/--espeak-dir/--whisper-dir/--kokoro-dir/
    --braille-pack-dir is still stripped from the compiled .exe -- only the
    portable ZIP output carries it. This is what makes an "Offline Edition"
    installer genuinely different from the regular one instead of a same-payload
    duplicate under a misleading name.
    """
    online = build_inno_setup_script("0.9.0", bundle_offline_components=False)
    offline = build_inno_setup_script("0.9.0", bundle_offline_components=True)

    online_excludes = next(line for line in online.splitlines() if line.startswith("Source:"))
    offline_excludes = next(line for line in offline.splitlines() if line.startswith("Source:"))

    optional_component_terms = (
        "tools\\pandoc\\*",
        "tools\\speech\\dectalk\\*",
        "tools\\speech\\espeak-ng\\*",
        "tools\\speech\\whispercpp\\*",
        "vendor\\braille-pack\\*",
        "kokoro-models\\*",
        "speech-models-bundled\\*",
        "wheels\\kokoro\\*",
        "wheels\\faster-whisper\\*",
        "wheels\\vosk\\*",
        "wheels\\mp3\\*",
    )
    for term in optional_component_terms:
        assert term in online_excludes, f"{term!r} must be excluded from the regular installer"
        assert term not in offline_excludes, f"{term!r} must NOT be excluded from --bundle-offline"
    # Piper has no build-time staging mechanism at all (no --piper-dir flag, no
    # wheelhouse) -- unlike the other five, --bundle-offline cannot lift this one
    # because there is nothing it could ever include. It stays excluded either way.
    assert "tools\\speech\\piper\\*" in online_excludes
    assert "tools\\speech\\piper\\*" in offline_excludes

    # Node.js has no --nodejs-dir staging flag on this script (it is not part of
    # the offline-speech/braille bundle) and the build-artifact/dev-only entries
    # are meaningless to ship either way, so both stay excluded regardless.
    for always_excluded in (
        "docs\\QUILL-PRD.md",
        "tools\\nodejs\\*",
        "_tool-download\\*",
        "_speech-download\\*",
        "*\\__pycache__\\*",
    ):
        assert always_excluded in online_excludes
        assert always_excluded in offline_excludes


def test_installer_clean_replaces_first_party_package_for_safe_upgrades() -> None:
    # Upgrade hygiene: Inno only overlays new [Files]; it never removes files a
    # new build no longer ships. The [InstallDelete] section must wipe our own
    # 'quill' package (where modules get renamed/moved/deleted between releases,
    # the proven cause of version-skew ImportError/AttributeError crashes) plus
    # stray __pycache__, so every install is a self-consistent copy of our code.
    script = build_inno_setup_script("9.9.9")
    # Anchor on the real section headers, not prose that mentions them.
    assert "\n[InstallDelete]\n" in script
    files_at = script.index("\n[Files]\n")
    install_delete_at = script.index("\n[InstallDelete]\n")
    # The InstallDelete section runs before [Files] re-lays the payload.
    assert install_delete_at < files_at
    install_delete = script[install_delete_at:files_at]
    assert 'Type: filesandordirs; Name: "{app}\\Lib\\site-packages\\quill"' in install_delete
    assert 'Type: filesandordirs; Name: "{app}\\__pycache__"' in install_delete
    # The live flat runtime at {app} root is overwritten in place by [Files]
    # (ignoreversion), not wiped -- re-extracting it every upgrade is slow for no
    # safety gain. But installing the flat build OVER a pre-flatten (nested)
    # install must remove the stale {app}\python runtime tree, or it lingers
    # forever as orphaned cruft. It holds no user data, so the wipe is safe.
    assert 'Type: filesandordirs; Name: "{app}\\python"' in install_delete


def test_installer_preserves_user_config_and_never_touches_the_data_dir() -> None:
    # Migration now protects config across releases (delta + schema version +
    # pre-migration backup), so the installer must NOT delete the user's config
    # or any user data. Nothing under %APPDATA%\Quill may be removed at install.
    script = build_inno_setup_script("9.9.9")
    install_delete = script[script.index("\n[InstallDelete]\n") : script.index("\n[Files]\n")]
    assert "{userappdata}\\Quill\\settings.json" not in install_delete
    assert "{userappdata}\\Quill\\keymap.json" not in install_delete
    assert "{userappdata}\\Quill\\features.json" not in install_delete
    assert "{userappdata}" not in install_delete


def test_uninstaller_offers_to_remove_custom_data_location() -> None:
    # A user who chose a custom data folder has its path recorded in
    # storage-mode.json under %APPDATA%\Quill (quill.core.storage_mode). That
    # pointer lives inside the very folder the uninstaller deletes, so the
    # uninstaller must read it BEFORE removing %APPDATA%\Quill -- otherwise the
    # custom directory is silently orphaned on "remove all data" (the bug this
    # guards against). The custom dir is then deleted, gated by the safety check.
    script = build_inno_setup_script("9.9.9")
    code = script[script.index("\n[Code]\n") :]
    assert "function ReadCustomDataDir(): String;" in code
    assert "storage-mode.json" in code
    # Only an explicit custom mode is honoured (appdata/portable carry no path).
    assert "'\"custom\"'" in code
    assert "IsSafeCustomDataDir(CustomDir)" in code
    assert "DelTree(CustomDir, True, True, True);" in code
    # The pointer read must precede the %APPDATA%\Quill deletion, or the file
    # would already be gone when we try to read it.
    assert code.index("CustomDir := ReadCustomDataDir()") < code.index("DelTree(DataDir")


def test_uninstaller_custom_data_guard_refuses_broad_targets() -> None:
    # The guard must never let a stray or hostile storage-mode.json point the
    # uninstaller at a drive root, the install dir, or a well-known shell folder.
    # Each is explicitly excluded, and only an existing directory more specific
    # than a bare drive root is eligible for deletion.
    script = build_inno_setup_script("9.9.9")
    code = script[script.index("\n[Code]\n") :]
    guard_at = code.index("function IsSafeCustomDataDir")
    guard = code[guard_at : code.index("\nend;", guard_at)]
    assert "if not DirExists(Dir) then" in guard  # must be a real existing dir
    assert "Length(N) <= 3" in guard  # rejects bare drive roots like c:\
    for constant in (
        "{app}",
        "{userappdata}",
        "{localappdata}",
        "{userprofile}",
        "{userdocs}",
        "{win}",
        "{sys}",
    ):
        assert constant in guard


def test_bundled_launcher_resolves_flat_self_running_quill_exe() -> None:
    # Regression guard for #722. The embedded runtime is flattened into {app}:
    # python313.dll / _pth / .pyd modules sit next to {app}\quill.exe, so it loads
    # its own interpreter and the sitecustomize hook self-runs QUILL. A NESTED
    # python\ layout orphaned the bundle-root quill.exe (it could not load the
    # interpreter) and broke launch. BundledLauncherPath must resolve the flat
    # {app}\quill.exe first, then {app}\pythonw.exe, and reference no python\ path.
    script = build_inno_setup_script("9.9.9")
    code = script[script.index("\n[Code]\n") :]
    fn = code[code.index("function BundledLauncherPath") :]
    fn = fn[: fn.index("\nend;")]
    assert "{app}\\python\\" not in fn, "launcher resolution must not use a nested python\\ path"
    i_root_quill = fn.index("{app}\\quill.exe")
    i_root_pythonw = fn.index("{app}\\pythonw.exe")
    assert i_root_quill < i_root_pythonw, (
        "BundledLauncherPath must prefer the flat {app}\\quill.exe self-runner"
    )


def test_installer_script_has_no_nested_python_launcher_path() -> None:
    # Strong, whole-script regression guard for #722: with the runtime flattened
    # into {app}, no generated installer line may reference a nested {app}\python\
    # path again (that nesting is what orphaned the bundle-root quill.exe).
    script = build_inno_setup_script("9.9.9")
    assert "{app}\\python\\" not in script


def test_self_run_sitecustomize_launches_quill_for_a_bare_exe() -> None:
    # The generated sitecustomize.py makes the portable quill.exe a self-running
    # launcher: no "-m quill", no console window, no .cmd flash. It must (a) only
    # act when the executable is quill.exe, (b) start QUILL via quill.__main__:main
    # on a bare double-click, and (c) leave python.exe / pip / "quill.exe -m quill"
    # untouched (the -m case has argv[0] == quill's __main__.py).
    from scripts.build_windows_distribution import _self_run_sitecustomize_source

    src = _self_run_sitecustomize_source()
    assert 'os.path.basename(sys.executable).lower() == "quill.exe"' in src
    assert "len(sys.argv) <= 1" in src
    assert "from quill.__main__ import main" in src
    assert "main()" in src
    assert '"__main__.py"' in src, "must skip the `quill.exe -m quill` path"
    # It must be importable, valid Python.
    compile(src, "sitecustomize.py", "exec")


def test_self_run_sitecustomize_opens_file_associations() -> None:
    # #729-adjacent (file association): setting quill.exe as the default app for a
    # document type makes the OS run `quill.exe "<doc>"`. Because quill.exe is a
    # renamed pythonw.exe, that path arrives as sys.argv[0] and Python would try
    # to run the document as a script. The hook must instead forward the document
    # to QUILL as a file to open.
    from scripts.build_windows_distribution import _self_run_sitecustomize_source

    src = _self_run_sitecustomize_source()
    assert "_associated_file" in src, "must detect an OS-passed document path"
    assert "os.path.isfile" in src, "only an existing file is treated as a document"
    assert 'sys.argv = ["quill", *paths]' in src, (
        "the document must be forwarded to QUILL via argv so __main__ opens it"
    )


def test_portable_bundle_flattens_runtime_to_root(tmp_path: Path, monkeypatch) -> None:
    # Regression guard for #722: the embedded runtime must be flattened into the
    # bundle root so the bundle-root quill.exe sits next to python313.dll/_pth and
    # self-runs. No nested python\ subdir may remain, and the portable-evidence
    # contract (quill.exe + data/ at the root) must hold.
    import scripts.build_windows_distribution as bwd

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "quill"\nversion = "1.2.3"\n', encoding="utf-8")
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "version.toml").write_text(
        'base_version = "1.2.3"\n'
        'channel = "stable"\n'
        "prerelease_number = 0\n"
        'product_name = "QUILL for All"\n'
        'publisher = "Community Access"\n',
        encoding="utf-8",
    )
    fake_kokoro = tmp_path / "kokoro-src"
    fake_kokoro.mkdir()
    (fake_kokoro / "kokoro-v1.0.int8.onnx").write_text("m", encoding="utf-8")
    (fake_kokoro / "voices-v1.0.bin").write_text("v", encoding="utf-8")
    # Fake every bundled tool dir so the offline test never downloads anything.
    tool_dirs = {}
    for tool_id, exe in {
        "pandoc": "pandoc.exe",
        "speech/dectalk": "say.exe",
        "speech/espeak-ng": "espeak-ng.exe",
        "speech/piper": "piper.exe",
        "speech/whispercpp": "whisper-cli.exe",
    }.items():
        d = tmp_path / tool_id.replace("/", "_")
        d.mkdir()
        (d / exe).write_text("bin", encoding="utf-8")
        tool_dirs[tool_id] = d

    # Stand in for the heavy embedded-python staging (download + pip): create a
    # python\ dir with representative runtime files, including the stamped
    # quill.exe and the self-run sitecustomize.py, so the test exercises the
    # flatten move rather than the network path.
    def fake_bundle_embedded_python(target_dir: Path, **_kwargs: object) -> Path:
        target_dir.mkdir(parents=True, exist_ok=True)
        for name in (
            "quill.exe",
            "pythonw.exe",
            "python.exe",
            "python313.dll",
            "python313.zip",
            "python313._pth",
            "sitecustomize.py",
        ):
            (target_dir / name).write_text(name, encoding="utf-8")
        (target_dir / "Lib" / "site-packages" / "quill").mkdir(parents=True)
        (target_dir / "Lib" / "site-packages" / "quill" / "__main__.py").write_text(
            "x", encoding="utf-8"
        )
        return target_dir

    monkeypatch.setattr(bwd, "bundle_embedded_python", fake_bundle_embedded_python)

    bwd.build_windows_distribution(
        pyproject,
        tmp_path / "dist",
        bundle_python=True,
        bundled_tool_dirs=tool_dirs,
        kokoro_dir=fake_kokoro,
    )

    portable = tmp_path / "dist" / "portable"
    assert not (portable / "python").exists(), "runtime must be flattened; no python\\ subdir"
    assert (portable / "quill.exe").is_file()
    assert (portable / "sitecustomize.py").is_file()
    assert (portable / "python313.dll").is_file()
    assert (portable / "python313._pth").is_file()
    assert (portable / "Lib" / "site-packages" / "quill" / "__main__.py").is_file()
    # Portable-evidence contract: quill.exe + a sibling data/ at the bundle root.
    assert (portable / "data").is_dir()


def test_shell_verb_registry_lines_cover_every_verb_and_extension() -> None:
    # SHELL-3: the installer's right-click verbs are generated straight from
    # the single core registry, so the menu can never drift from the CLI.
    lines = build_shell_verb_registry_lines()
    text = "\n".join(lines)
    for verb in default_shell_verbs():
        key = f"shell\\Quill.{verb.verb_id}"
        # Each verb appears with its label and its --action launch command.
        assert f'ValueData: "{verb.label}"' in text
        assert f"--action {verb.action} " in text
        for extension in verb.extensions:
            base = f"Software\\Classes\\SystemFileAssociations\\{extension}\\{key}"
            assert f'Subkey: "{base}"' in text
            assert f'Subkey: "{base}\\command"' in text


def test_shell_verb_registry_lines_are_optin_and_uninstall_clean() -> None:
    # Every verb key is gated behind the opt-in shellverbs task and tagged
    # uninsdeletekey so a full uninstall removes the context-menu entries.
    lines = build_shell_verb_registry_lines()
    assert lines, "expected at least one generated verb registry line"
    assert all("Tasks: shellverbs" in line for line in lines)
    # The verb root keys (not the MUIVerb/command values) carry uninsdeletekey.
    root_key_lines = [line for line in lines if 'ValueName: ""' in line and "\\command" not in line]
    assert root_key_lines
    assert all("Flags: uninsdeletekey" in line for line in root_key_lines)


def test_shell_verb_command_launches_quill_exe_with_action() -> None:
    # The launch command routes through quill.exe (AppExeName), a stamped copy of
    # pythonw.exe. It MUST pass "-m quill" before "--action" so pythonw runs QUILL
    # with the verb + file as arguments; without it pythonw rejects "--action" as
    # an unknown option (or tries to run %1 as a script). See the launcher contract.
    lines = build_shell_verb_registry_lines()
    command_lines = [line for line in lines if "\\command" in line]
    assert command_lines
    for line in command_lines:
        assert 'ValueData: """{app}\\{#AppExeName}"" -m quill --action ' in line
        assert '""%1"""' in line


def test_inno_setup_script_includes_shell_verb_task_and_registry() -> None:
    # SHELL-3 is wired end-to-end into the generated installer script.
    script = build_inno_setup_script("9.9.9")
    assert 'Name: "shellverbs"; Description: "Add ""Send to Quill"" actions' in script
    assert 'Send to Quill" file right-click verbs (SHELL-3)' in script
    # Spot-check one concrete verb/extension pair made it into the [Registry].
    assert 'Subkey: "Software\\Classes\\SystemFileAssociations\\.png\\shell\\Quill.ocr"' in script
    assert "--action ocr " in script


@pytest.mark.skipif(
    not _VERSION_TOML.exists(),
    reason="build/version.toml absent (local-only canonical source); iss identity cannot be re-derived",
)
def test_committed_installer_iss_is_in_sync_with_generator() -> None:
    # #114 / SHELL-1: installer/quill.iss carries a "Generated by ...; Edit
    # build_inno_setup_script()" header, so the committed file must be the exact
    # output of the generator for its declared version. This guard fails if the
    # generator changes (e.g. a new shell verb or extension) without the
    # committed installer being regenerated, preventing a silent drift between
    # the shipped Explorer context menu and the single core verb registry.
    repo_root = Path(__file__).resolve().parents[3]
    committed = (repo_root / "installer" / "quill.iss").read_text(encoding="utf-8")

    version_match = re.search(r'#define AppVersion "([^"]+)"', committed)
    assert version_match, "committed installer is missing an AppVersion define"
    version = version_match.group(1)

    # The generator pulls product_name / publisher from build/version.toml,
    # so re-derive them through the same source for a true equality check.
    from scripts.build_windows_distribution import _build_identity

    identity = _build_identity(repo_root)
    generated = build_inno_setup_script(
        version,
        product_name=identity.product_name,
        publisher=identity.publisher,
        numeric_version=f"{identity.base_version}.{identity.prerelease_number}",
    )
    assert committed.strip() == generated.strip(), (
        "installer/quill.iss is out of sync with build_inno_setup_script(); "
        "regenerate it (the file is generated, not hand-edited)."
    )


def test_build_windows_distribution_can_bundle_external_tools(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "quill"
version = "3.0.0"
""".strip(),
        encoding="utf-8",
    )
    fake_pandoc_dir = tmp_path / "pandoc"
    fake_pandoc_dir.mkdir()
    (fake_pandoc_dir / "pandoc.exe").write_text("binary", encoding="utf-8")
    fake_kokoro_dir = tmp_path / "kokoro-src"
    fake_kokoro_dir.mkdir()
    (fake_kokoro_dir / "kokoro-v1.0.int8.onnx").write_text("model", encoding="utf-8")
    (fake_kokoro_dir / "voices-v1.0.bin").write_text("voices", encoding="utf-8")

    bundle = build_windows_distribution(
        pyproject,
        tmp_path / "dist",
        bundled_tool_dirs={"pandoc": fake_pandoc_dir},
        kokoro_dir=fake_kokoro_dir,
    )

    manifest = json.loads(
        (tmp_path / "dist" / "portable" / "manifest.json").read_text(encoding="utf-8")
    )
    assert "pandoc" in manifest["bundledTools"]
    # Piper is no longer auto-staged (PRD 10.2.x unbundle): only explicitly
    # passed tool dirs are bundled, so a pandoc-only build bundles pandoc alone.
    assert "speech/piper" not in manifest["bundledTools"]
    # DECtalk and eSpeak-NG are unbundled (PRD 10.2.4): not staged by default, so
    # not marked bundled, but still flagged downloadable for on-demand acquisition.
    assert manifest["speechAssets"]["dectalk"]["bundled"] is False
    assert manifest["speechAssets"]["dectalk"]["downloadable"] is True
    assert manifest["speechAssets"]["espeak"]["bundled"] is False
    assert manifest["speechAssets"]["espeak"]["downloadable"] is True
    # Kokoro is staged to the bundle root, not tools/, and not via bundledTools.
    assert manifest["speechAssets"]["kokoro"]["bundled"] is True
    assert (tmp_path / "dist" / "portable" / "kokoro-models" / "voices-v1.0.bin").exists()
    assert (tmp_path / "dist" / "portable" / "tools" / "pandoc" / "pandoc.exe").exists()
    assert bundle["portable_dir"] == str(tmp_path / "dist" / "portable")


def test_find_inno_setup_compiler_checks_common_locations(monkeypatch, tmp_path: Path) -> None:
    compiler = tmp_path / "ISCC.exe"
    compiler.write_text("binary", encoding="utf-8")
    monkeypatch.setattr("scripts.build_windows_distribution.shutil.which", lambda _name: None)
    monkeypatch.setattr(
        "scripts.build_windows_distribution.Path.exists",
        lambda self: self == compiler,
    )
    monkeypatch.setattr(
        "scripts.build_windows_distribution.Path",
        lambda value: compiler if "Inno Setup" in str(value) else Path(value),
    )

    discovered = find_inno_setup_compiler()

    assert discovered == compiler


def test_compile_inno_setup_installer_runs_compiler(monkeypatch, tmp_path: Path) -> None:
    installer_script = tmp_path / "quill.iss"
    installer_script.write_text("script", encoding="utf-8")
    compiler = tmp_path / "ISCC.exe"
    compiler.write_text("binary", encoding="utf-8")
    installer_exe = tmp_path / "Quill-for-All-Setup-0.1.exe"

    def fake_run(command: list[str], check: bool) -> None:
        assert check is True
        assert command == [str(compiler), str(installer_script)]
        installer_exe.write_text("exe", encoding="utf-8")

    monkeypatch.setattr("scripts.build_windows_distribution.subprocess.run", fake_run)

    built = compile_inno_setup_installer(
        installer_script,
        version="0.1",
        iscc_path=compiler,
    )

    assert built == installer_exe


def test_compile_inno_setup_installer_accepts_inno_output_folder(
    monkeypatch,
    tmp_path: Path,
) -> None:
    installer_script = tmp_path / "quill.iss"
    installer_script.write_text("script", encoding="utf-8")
    compiler = tmp_path / "ISCC.exe"
    compiler.write_text("binary", encoding="utf-8")
    output_dir = tmp_path / "Output"
    output_dir.mkdir()
    installer_exe = output_dir / "Quill-for-All-Setup-0.1.exe"

    def fake_run(command: list[str], check: bool) -> None:
        assert check is True
        assert command == [str(compiler), str(installer_script)]
        installer_exe.write_text("exe", encoding="utf-8")

    monkeypatch.setattr("scripts.build_windows_distribution.subprocess.run", fake_run)

    built = compile_inno_setup_installer(
        installer_script,
        version="0.1",
        iscc_path=compiler,
    )

    assert built == installer_exe


def test_prune_keeps_babel_but_removes_true_build_only_packages(tmp_path: Path) -> None:
    """babel must survive the prune; genuinely build-only packages are removed.

    babel looks build-only (we compile translations with it; QUILL's own i18n
    uses stdlib ``gettext``), but ``kokoro-onnx`` imports it transitively at
    runtime (``kokoro_onnx -> phonemizer -> segments -> csvw -> babel.numbers``).
    Pruning it broke Kokoro's onnx path on a clean build (#881), so this guards
    that babel stays while a real build-only package like ``setuptools`` is still
    removed and a runtime package like ``wx`` is untouched.
    """
    site_packages = tmp_path / "site-packages"
    site_packages.mkdir()
    (site_packages / "babel").mkdir()
    (site_packages / "babel" / "numbers.py").write_text("x = 1", encoding="utf-8")
    (site_packages / "Babel-2.18.0.dist-info").mkdir()
    (site_packages / "Babel-2.18.0.dist-info" / "RECORD").write_text("", encoding="utf-8")
    (site_packages / "setuptools").mkdir()  # genuinely build-only -> pruned
    (site_packages / "setuptools" / "__init__.py").write_text("x = 1", encoding="utf-8")
    (site_packages / "wx").mkdir()
    (site_packages / "wx" / "__init__.py").write_text("core = 1", encoding="utf-8")

    _prune_embedded_runtime(site_packages)

    assert (site_packages / "babel").exists()  # kokoro-onnx needs it at runtime (#881)
    assert (site_packages / "Babel-2.18.0.dist-info").exists()
    assert not (site_packages / "setuptools").exists()  # build-only, pruned
    assert (site_packages / "wx").exists()  # runtime package untouched


def test_quill_own_modules_never_import_babel() -> None:
    """QUILL's own i18n uses stdlib gettext, not babel (babel now ships only for
    kokoro-onnx's transitive use). This documents that QUILL doesn't add a direct
    babel dependency of its own.
    """
    repo_root = Path(__file__).resolve().parents[3]
    runtime_dirs = ["core", "ui", "io", "platform", "stability", "plugins"]
    offenders: list[str] = []
    for sub in runtime_dirs:
        base = repo_root / "quill" / sub
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"^\s*(import babel|from babel\b)", text, re.MULTILINE):
                offenders.append(str(path.relative_to(repo_root)))
    assert offenders == [], f"runtime modules import babel: {offenders}"


def test_bundled_runtime_dependencies_uses_runtime_groups(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "quill"
version = "0.1"
dependencies = ["alpha>=1.0"]

[project.optional-dependencies]
ui = ["wxPython>=4.2.2", "pyttsx3>=2.99"]
spellcheck = ["pyenchant>=3.2"]
dev = ["pytest>=8.2"]
""".strip(),
        encoding="utf-8",
    )

    dependencies = bundled_runtime_dependencies(pyproject)

    assert dependencies == ["alpha>=1.0", "wxPython>=4.2.2", "pyttsx3>=2.99", "pyenchant>=3.2"]


def test_build_identity_reads_canonical_version_toml(tmp_path: Path) -> None:
    """Installer metadata must come from build/version.toml, not literals."""
    from scripts.build_windows_distribution import _build_identity

    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "version.toml").write_text(
        'base_version = "0.7.0"\n'
        'channel = "rc"\n'
        "prerelease_number = 2\n"
        'product_name = "QUILL for All"\n'
        'publisher = "Community Access"\n',
        encoding="utf-8",
    )

    identity = _build_identity(tmp_path)

    assert identity.base_version == "0.7.0"
    assert identity.channel == "rc"
    assert identity.prerelease_number == 2
    assert identity.display_version == "0.7.0 Release Candidate 2"
    assert identity.product_name == "QUILL for All"
    assert identity.publisher == "Community Access"


def test_build_identity_falls_back_when_version_toml_missing(tmp_path: Path) -> None:
    """Missing version.toml must not crash; fall back to defaults."""
    from scripts.build_windows_distribution import _build_identity

    identity = _build_identity(tmp_path)

    assert identity.base_version == "unknown"
    assert identity.channel == "dev"
    assert identity.display_version == "unknown Dev"
    assert identity.product_name == "QUILL for All"
    assert identity.publisher == "Community Access"


def test_build_inno_setup_script_uses_identity_defaults(tmp_path: Path) -> None:
    """The script's defaults must match branding constants, not the old literals."""
    from scripts.build_windows_distribution import build_inno_setup_script

    script = build_inno_setup_script("0.7.0 Beta 1")

    assert '#define AppName "QUILL for All"' in script
    assert '#define AppPublisher "Community Access"' in script
    assert "Blind Information Technology Solutions" not in script
    assert '#define AppName "Quill"' not in script
    assert "OutputBaseFilename=Quill-for-All-Setup-0.7.0 Beta 1" in script


def test_file_association_launches_root_quill_exe_next_to_python_dll() -> None:
    """Regression guard for #740 (python313.dll missing on Explorer 'Open with').

    The runtime is flattened so quill.exe sits at {app} next to its own
    python313.dll. Launching a file from Explorer must therefore invoke that
    ROOT launcher (not a nested ``python`` sub-path and not something CWD-dependent),
    so the Windows loader finds the DLL on an external launch — the exact case
    the report failed on before the flatten. If a future change points the
    association at a nested launcher, the missing-DLL error returns; this locks
    the invariant in.
    """
    script = build_inno_setup_script("9.9.9")

    # The launcher the association points at is the flattened root quill.exe.
    assert '#define AppExeName "quill.exe"' in script

    # The "Open with" command and every shell-verb open command invoke the ROOT
    # launcher ({app}\quill.exe), which is co-located with python313.dll.
    assert r"Applications\{#AppExeName}\shell\open\command" in script
    assert r'"{app}\{#AppExeName}"" -m quill' in script

    # No file-launch command may target a NESTED launcher path — that layout
    # (quill.exe not beside python313.dll) is what broke external launch.
    assert r"{app}\python\{#AppExeName}" not in script
    assert r"{app}\python\quill.exe" not in script
    assert r"{app}\python\pythonw.exe" not in script


def test_kokoro_is_not_bundled_and_installs_on_demand() -> None:
    """Kokoro (kokoro-onnx + onnxruntime + phonemizer + babel) is large and
    optional. It installs on demand via install_kokoro_onnx() into an engine-pack;
    bundling it re-bloats the installer. Guard that it stays out of the bundled
    dependency groups (the footprint fix behind #881)."""
    from scripts.build_windows_distribution import DEFAULT_BUNDLED_DEPENDENCY_GROUPS

    assert "kokoro" not in DEFAULT_BUNDLED_DEPENDENCY_GROUPS
    # The engines users actually need offline stay bundled.
    assert "speech" in DEFAULT_BUNDLED_DEPENDENCY_GROUPS
    assert "ui" in DEFAULT_BUNDLED_DEPENDENCY_GROUPS


@pytest.mark.parametrize(
    ("name", "requirements"),
    [
        ("kokoro", KOKORO_WHEELHOUSE_REQUIREMENTS),
        ("faster-whisper", FASTER_WHISPER_WHEELHOUSE_REQUIREMENTS),
        ("vosk", VOSK_WHEELHOUSE_REQUIREMENTS),
        ("mp3", MP3_WHEELHOUSE_REQUIREMENTS),
    ],
)
def test_stage_pip_wheelhouse_runs_pip_download(
    monkeypatch, tmp_path: Path, name: str, requirements: tuple[str, ...]
) -> None:
    """--bundle-offline stages an on-demand engine's pip package tree as local
    wheels, using the *same* interpreter that will later install them (so wheel
    tags match) -- the fix for the Offline Edition still needing PyPI to
    actually use Kokoro, Faster Whisper, Vosk, or MP3 support."""
    captured: dict = {}

    def fake_run(command, *, check):
        captured["command"] = list(command)
        assert check is True
        # Simulate pip download actually producing a wheel.
        target = Path(command[command.index("--dest") + 1])
        (target / "fake_wheel-0.1-py3-none-any.whl").write_bytes(b"fake wheel")

    monkeypatch.setattr("scripts.build_windows_distribution.subprocess.run", fake_run)
    portable_dir = tmp_path / "portable"
    python_exe = tmp_path / "python.exe"
    result = _stage_pip_wheelhouse(portable_dir, python_exe, name, requirements)

    assert result is True
    cmd = captured["command"]
    assert cmd[0] == str(python_exe)
    assert cmd[1:4] == ["-m", "pip", "download"]
    assert "--only-binary=:all:" in cmd
    for req in requirements:
        assert req in cmd
    assert list((portable_dir / "wheels" / name).glob("*.whl"))


def test_stage_pip_wheelhouse_reuses_already_staged(monkeypatch, tmp_path: Path) -> None:
    portable_dir = tmp_path / "portable"
    target = portable_dir / "wheels" / "kokoro"
    target.mkdir(parents=True)
    (target / "existing-0.1-py3-none-any.whl").write_bytes(b"x")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("pip download should not run when already staged")

    monkeypatch.setattr("scripts.build_windows_distribution.subprocess.run", fail_if_called)
    assert (
        _stage_pip_wheelhouse(
            portable_dir, tmp_path / "python.exe", "kokoro", KOKORO_WHEELHOUSE_REQUIREMENTS
        )
        is True
    )


def test_speech_asset_manifest_reports_wheelhouse_presence(tmp_path: Path) -> None:
    portable_dir = tmp_path / "portable"
    portable_dir.mkdir()
    manifest = _speech_asset_manifest(portable_dir, [])
    assert manifest["kokoro_wheelhouse"]["bundled"] is False

    wheel_dir = portable_dir / "wheels" / "kokoro"
    wheel_dir.mkdir(parents=True)
    (wheel_dir / "soundfile-0.14.0-py3-none-any.whl").write_bytes(b"x")
    manifest = _speech_asset_manifest(portable_dir, [])
    assert manifest["kokoro_wheelhouse"]["bundled"] is True
    assert manifest["kokoro_wheelhouse"]["path"] == str(wheel_dir)


def test_speech_asset_manifest_reports_whisper_model_presence(tmp_path: Path) -> None:
    portable_dir = tmp_path / "portable"
    portable_dir.mkdir()
    manifest = _speech_asset_manifest(portable_dir, [])
    assert manifest["whispercpp_model"]["bundled"] is False

    model_dir = portable_dir / "speech-models-bundled" / "whispercpp"
    model_dir.mkdir(parents=True)
    model_path = model_dir / f"ggml-{DEFAULT_BUNDLED_WHISPER_MODEL_ID}.bin"
    model_path.write_bytes(b"x")
    manifest = _speech_asset_manifest(portable_dir, [])
    assert manifest["whispercpp_model"]["bundled"] is True
    assert manifest["whispercpp_model"]["path"] == str(model_path)


def test_stage_whisper_model_downloads_and_verifies(monkeypatch, tmp_path: Path) -> None:
    """--bundle-offline auto-fetches the default whisper.cpp GGML model (no
    --whisper-dir needed, unlike the engine binary) so the Offline Edition's
    required default transcription engine has something to transcribe with
    immediately after install."""
    captured: dict = {}

    def fake_download(url, target, expected_sha256):
        captured["url"] = url
        captured["target"] = target
        captured["sha256"] = expected_sha256
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"fake ggml model")

    monkeypatch.setattr(
        "scripts.build_windows_distribution._download_with_verification", fake_download
    )
    portable_dir = tmp_path / "portable"
    result = _stage_whisper_model(portable_dir)

    assert result is True
    target = (
        portable_dir
        / "speech-models-bundled"
        / "whispercpp"
        / f"ggml-{DEFAULT_BUNDLED_WHISPER_MODEL_ID}.bin"
    )
    assert target.is_file()
    assert captured["target"] == target
    assert captured["sha256"]
    assert "huggingface.co" in captured["url"]
    assert DEFAULT_BUNDLED_WHISPER_MODEL_ID in captured["url"] or "ggml-tiny.bin" in captured["url"]


def test_stage_piper_offline_stages_engine_and_starter_voice(monkeypatch, tmp_path: Path) -> None:
    """--bundle-offline auto-stages Piper's SHA-pinned engine zip plus a
    starter voice pair, closing the last tracked speech gap in the Offline
    Edition (Piper previously always needed the internet on first use)."""
    from quill.core.speech.piper_install import PIPER_DOWNLOAD_SHA256
    from scripts.build_windows_distribution import _stage_piper_offline

    calls: list[tuple[str, Path, str | None]] = []

    def fake_download(url, target, expected_sha256):
        calls.append((url, target, expected_sha256))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"fake payload")

    monkeypatch.setattr(
        "scripts.build_windows_distribution._download_with_verification", fake_download
    )
    portable_dir = tmp_path / "portable"
    assert _stage_piper_offline(portable_dir) is True

    root = portable_dir / "speech-models-bundled" / "piper"
    assert (root / "piper_windows_amd64.zip").is_file()
    assert (root / "voices" / "en_US-lessac-medium.onnx").is_file()
    assert (root / "voices" / "en_US-lessac-medium.onnx.json").is_file()
    # The engine zip is verified against the runtime's own pinned hash; the
    # voice URLs are the exact HuggingFace paths the runtime download uses.
    assert calls[0][2] == PIPER_DOWNLOAD_SHA256
    assert all("huggingface.co/rhasspy/piper-voices" in url for url, _t, _s in calls[1:])
    # Already-staged files are reused (no re-download on a second run).
    calls.clear()
    assert _stage_piper_offline(portable_dir) is True
    assert calls == []


def test_stage_whisper_model_reuses_already_staged(monkeypatch, tmp_path: Path) -> None:
    portable_dir = tmp_path / "portable"
    target = (
        portable_dir
        / "speech-models-bundled"
        / "whispercpp"
        / f"ggml-{DEFAULT_BUNDLED_WHISPER_MODEL_ID}.bin"
    )
    target.parent.mkdir(parents=True)
    target.write_bytes(b"already here")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("download should not run when already staged")

    monkeypatch.setattr(
        "scripts.build_windows_distribution._download_with_verification", fail_if_called
    )
    assert _stage_whisper_model(portable_dir) is True


def test_dev_cache_ignore_excludes_local_tool_caches_but_keeps_real_source(
    tmp_path: Path,
) -> None:
    """A contributor's local mypy/pytest/ruff caches (or stray __pycache__)
    must never leak into a shipped build via the quill/ source copy -- they're
    only present because tools happened to run on this machine, and a mypy
    cache alone can be tens of MB of pure bloat for an end user."""
    from scripts.build_windows_distribution import _DEV_CACHE_IGNORE

    source = tmp_path / "quill"
    (source / "core").mkdir(parents=True)
    (source / "core" / "settings.py").write_text("x = 1\n", encoding="utf-8")
    (source / "__pycache__").mkdir()
    (source / "__pycache__" / "settings.cpython-313.pyc").write_bytes(b"\x00")
    (source / "io" / ".mypy_cache" / "3.13").mkdir(parents=True)
    (source / "io" / ".mypy_cache" / "3.13" / "settings.data.json").write_text(
        "{}", encoding="utf-8"
    )
    (source / ".pytest_cache").mkdir()
    (source / ".ruff_cache").mkdir()

    dest = tmp_path / "copied"
    import shutil

    shutil.copytree(source, dest, ignore=_DEV_CACHE_IGNORE)

    assert (dest / "core" / "settings.py").exists()
    assert not (dest / "__pycache__").exists()
    assert not (dest / "io" / ".mypy_cache").exists()
    assert not (dest / ".pytest_cache").exists()
    assert not (dest / ".ruff_cache").exists()


# ---------------------------------------------------------------------------
# Feedback-token build guard (#919: beta-2 upgrades shipped a tokenless
# Report a Bug). The token is now ALWAYS required -- a distributable must bake
# a non-empty BUNDLED_TOKEN on every build, with no opt-out. These lock the
# helper that enforces it at the point that matters -- the file that actually
# ships inside the bundled quill/ package.
# ---------------------------------------------------------------------------


def test_bundled_token_value_reads_a_real_token(tmp_path: Path) -> None:
    token_file = tmp_path / "_feedback_token.py"
    token_file.write_text('BUNDLED_TOKEN = "ghp_secretvalue"\n', encoding="utf-8")
    assert _bundled_token_value(token_file) == "ghp_secretvalue"


def test_bundled_token_value_treats_empty_and_missing_as_empty(tmp_path: Path) -> None:
    empty = tmp_path / "_feedback_token.py"
    empty.write_text('BUNDLED_TOKEN = ""\n', encoding="utf-8")
    assert _bundled_token_value(empty) == ""
    # The committed repo default IS the empty token (the file is gitignored-but-
    # tracked empty); this is exactly the tokenless state the build must refuse
    # to ship, so a missing file must also read as empty, never as "present".
    assert _bundled_token_value(tmp_path / "does_not_exist.py") == ""


def test_build_guard_refuses_an_empty_token(tmp_path: Path) -> None:
    # The guard must fail when the bundled token file is empty -- the exact
    # "No token" upgrade symptom. There is no opt-out.
    (tmp_path / "quill").mkdir()
    (tmp_path / "quill" / "_feedback_token.py").write_text('BUNDLED_TOKEN = ""\n', encoding="utf-8")
    with pytest.raises(RuntimeError, match="empty BUNDLED_TOKEN"):
        _assert_bundled_token_nonempty(tmp_path)


def test_build_guard_refuses_a_missing_token_file(tmp_path: Path) -> None:
    # A build that never copied the token into the bundle is just as broken as
    # an empty one; the guard must catch it (not silently ship tokenless).
    with pytest.raises(RuntimeError, match="missing from the runtime"):
        _assert_bundled_token_nonempty(tmp_path)


def test_build_guard_accepts_a_real_token(tmp_path: Path) -> None:
    (tmp_path / "quill").mkdir()
    (tmp_path / "quill" / "_feedback_token.py").write_text(
        'BUNDLED_TOKEN = "ghp_realtoken"\n', encoding="utf-8"
    )
    # Must not raise -- a real token ships fine.
    _assert_bundled_token_nonempty(tmp_path)
