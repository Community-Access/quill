; Quill Radio installer -- shared-runtime layout.
;
; Promoted from the validation-only quill-radio-shared.iss (2026-07-24):
; every shipping QuillVille product now installs the shared QuillVille
; Runtime once (at %LOCALAPPDATA%\QuillVille\Runtime\) and launches
; through it, instead of shipping a private Python inside its own
; onedir. The install-if-absent + reference-counting is owned by
; installer\shared-runtime.iss; this script's only job is to declare
; the three identifiers the fragment needs (RuntimeVersion,
; RuntimeSourceDir, AppRefId) and `#include` the fragment.
;
; The per-app payload is tiny: just the icon, the per-app C launcher
; (QuillRadio.exe, the portable-mode anchor; see
; storage_mode._has_portable_evidence), and (optionally) docs. The
; radio code itself lives in the shared runtime, launched via
; `{code:RuntimeExe} -m quill.apps.radio`.
;
; Build inputs (must exist before ISCC runs):
;   - the shared runtime at ..\..\runtime\dist\QuillVilleRuntime (built
;     by ..\..\runtime\quillville-runtime.spec, marker stamped,
;     ffmpeg/mpv staged into its tools\ so Radio finds them via
;     QUILL_APP_ROOT);
;   - the per-app QuillRadio.exe at ..\dist\QuillRadio\QuillRadio.exe
;     (built by build_native_launcher.py);
;   - the per-app icon at ..\assets\quill-radio.ico;
;   - the rendered Radio docs at ..\dist\QuillRadio\docs.
;
; The standalone \scripts\build_release.ps1 chains those steps before
; the ISCC call; running ISCC directly requires all of them to exist
; already.

#define AppName "Quill Radio"
; Version is single-sourced from build_release.ps1, which passes
; /dAppVersion=<version> to ISCC. The literal below is only the fallback for a
; manual ISCC run and must be kept in step with build_release.ps1's $version.
#ifndef AppVersion
  #define AppVersion "3.0.0"
#endif
#define AppPublisher "Community Access"
#define AppURL "https://github.com/Community-Access/quill-radio"

; -- shared runtime parameters (read by installer\shared-runtime.iss) ----------
; AppRefId is the stable per-app key the fragment uses in
; runtime.state.json. It MUST stay "radio" forever -- renaming it
; would orphan the previous reference and double-count, leaving a
; phantom install that the uninstaller cannot reclaim.
#define RuntimeVersion "3.13.15"
#define RuntimeSourceDir "..\..\runtime\dist\QuillVilleRuntime"
#define AppRefId "radio"
; The media tools Radio declares (quill.apps.radio REQUIRED_COMPONENTS =
; ("ffmpeg", "mpv")). shared-runtime.iss installs these unconditionally, so
; Radio gets its playback engine whatever order the apps were installed in.
#define ToolFfmpeg
#define ToolMpv

[Setup]
#ifdef Sign
; Code signing (opt-in). Present only when ISCC is invoked with /DSign plus a
; matching /Squilltrusted=<sign command>; Inno then signs the compiled Setup.exe
; and the generated uninstaller. A plain build passes neither, so these
; directives are absent and the unsigned build compiles unchanged. See
; docs/code-signing.md.
SignTool=quilltrusted
SignedUninstaller=yes
#endif
; Same AppId as the legacy onedir installer: it is the same product, so
; installing this variant upgrades an existing Radio in place rather than
; sitting beside it.
AppId={{35DAB52F-94BB-475C-BA97-A5059C85B3D1}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
VersionInfoVersion=3.0.0.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} accessible internet radio (shared runtime)
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableDirPage=no
DisableProgramGroupPage=auto
AllowNoIcons=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
; The -Shared suffix matches the validation variant that was authored
; in quill-radio-shared.iss; once the shared-runtime install is the
; only shipping layout (Phase 2 ships today; Phase 4 drops the
; PyInstaller bootloader), drop the -Shared so Radio and the other
; products' installers line up.
OutputBaseFilename=Quill-Radio-Setup-Shared-{#AppVersion}
; A 64-bit Setup (Inno 7) so the LZMA dictionary can exceed the 32-bit cap.
; 128 MB reaches across ffmpeg.exe -> ffprobe.exe (97 MB of near-identical
; bytes the 32 MB ultra dictionary could never dedupe): 208.7 -> 181.8 MB
; measured on the 3.0.0 payload (2026-08-17). Costs the end user a 128 MB
; decompression buffer during install; the x64compatible line above already
; restricts installs to machines that have it.
SetupArchitecture=x64
Compression=lzma2/ultra
LZMADictionarySize=131072
SolidCompression=yes
WizardStyle=modern
CloseApplications=force
RestartApplications=no
UninstallDisplayName={#AppName} {#AppVersion}
UninstallDisplayIcon={app}\quill-radio.ico
SetupIconFile=..\assets\quill-radio.ico
LicenseFile=..\LICENSE
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Types]
Name: "full"; Description: "Full installation (recommended)"
Name: "compact"; Description: "Compact installation (program only, no bundled documentation)"
Name: "custom"; Description: "Custom installation"; Flags: iscustom

[Components]
; The runtime component is Flags: fixed -- it is part of every install
; type. Without it the per-app C launcher has no Python to spawn, and
; the app cannot launch. Disabling the "runtime" component is only
; useful on a Modify run when the user has uninstalled every other
; QuillVille app and wants the shared runtime removed (the fragment's
; CurUninstallStepChanged handles the unregister then).
Name: "runtime"; Description: "Shared QuillVille runtime (Python) -- installed once, reused by every QuillVille app"; Types: full compact custom; Flags: fixed
Name: "main"; Description: "{#AppName} (required)"; Types: full compact custom; Flags: fixed
Name: "docs"; Description: "Documentation (User Guide, Release Notes, Product Requirements)"; Types: full custom

[Files]
; Radio's own payload is tiny: just its icon, the per-app C launcher
; (the portable-mode anchor), and (optionally) its docs. The program
; itself lives in the shared runtime, installed by the fragment below.
Source: "..\assets\quill-radio.ico"; DestDir: "{app}"; Components: main; Flags: ignoreversion
Source: "..\dist\QuillRadio\QuillRadio.exe"; DestDir: "{app}"; Components: main; Flags: ignoreversion
; Which edition this is, so Check for Updates offers THIS installer back
; rather than guessing from a file extension (a user got the thin setup
; after installing the full one; see core/install_edition.py).
Source: "..\installer\edition-installer-full.txt"; DestDir: "{app}"; DestName: "quill-edition.txt"; Components: main; Flags: ignoreversion
Source: "..\dist\QuillRadio\docs\*"; DestDir: "{app}\docs"; Components: docs; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "*.epub"

; The shared runtime (install-if-absent) + reference registration + orphan
; removal on uninstall. Defines RuntimeDir/RuntimeExe used by [Icons]/[Run].
#include "..\..\..\installer\shared-runtime.iss"

[Icons]
; Every shortcut launches through the shared runtime. WorkingDir is the
; shared runtime dir so `python -m quill.apps.radio` finds the per-app
; quill package at the shared location's sitecustomize path.
Name: "{group}\{#AppName}"; Filename: "{code:RuntimeExe}"; Parameters: "-m quill.apps.radio"; WorkingDir: "{code:RuntimeDir}"; IconFilename: "{app}\quill-radio.ico"; Components: main
Name: "{group}\{#AppName} User Guide"; Filename: "{app}\docs\userguide.md"; Components: docs
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{code:RuntimeExe}"; Parameters: "-m quill.apps.radio"; WorkingDir: "{code:RuntimeDir}"; IconFilename: "{app}\quill-radio.ico"; Tasks: desktopicon; Components: main

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{code:RuntimeExe}"; Parameters: "-m quill.apps.radio"; Description: "Launch {#AppName}"; Flags: postinstall nowait skipifsilent unchecked

[UninstallDelete]
; Remove only Radio's own {app} payload. The shared runtime is left to
; the fragment's CurUninstallStepChanged, which deletes it only when
; unreferenced (no other QuillVille app still references the version
; that was registered at install time). The {app}\_internal tree that
; the old onedir layout used is gone in the shared layout -- the
; fragment owns the runtime files, not {app} -- so no upgrade hygiene
; is needed here.
Type: filesandordirs; Name: "{app}"

; Radio shares its settings/favorites/recordings store (%APPDATA%\Quill)
; with QUILL and the other apps; uninstall never touches that data.
; The full QUILL uninstaller owns that decision (it is the only
; uninstaller that knows the user's preferences).
