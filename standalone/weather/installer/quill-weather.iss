; Quill Weather installer -- shared-runtime layout.
;
; Promoted from the onedir layout to the shared QuillVille Runtime
; (2026-07-24). See standalone\radio\installer\quill-radio.iss for the
; full rationale; Weather follows the same pattern (per-app C launcher
; + docs only; the program itself lives in the shared runtime, launched
; via `{code:RuntimeExe} -m quill.apps.weather`). Weather is small -- no
; ffmpeg or mpv engine to ship -- so the per-app payload is just the
; icon, the C launcher, and (optionally) docs.
;
; Build inputs (must exist before ISCC runs):
;   - the shared runtime at ..\..\runtime\dist\QuillVilleRuntime
;     (built by ..\..\runtime\quillville-runtime.spec, marker stamped;
;     build_runtime.ps1 chains the spec, the marker stamp, and the
;     ffmpeg/mpv stage);
;   - the per-app QuillWeather.exe at ..\dist\QuillWeather\QuillWeather.exe
;     (built by build_native_launcher.py);
;   - the per-app icon at ..\assets\quill-weather.ico;
;   - the rendered Weather docs at ..\dist\QuillWeather\docs.

#define AppName "Quill Weather"
; Version is single-sourced from build_release.ps1, which passes
; /dAppVersion=<version> to ISCC. The literal below is only the fallback for a
; manual ISCC run and must be kept in step with build_release.ps1's $version.
#ifndef AppVersion
  #define AppVersion "2.2.0"
#endif
#define AppPublisher "Community Access"
#define AppURL "https://github.com/Community-Access/quill-weather"

; -- shared runtime parameters (read by installer\shared-runtime.iss) ----------
; AppRefId is the stable per-app key the fragment uses in
; runtime.state.json. It MUST stay "weather" forever -- renaming it
; would orphan the previous reference and double-count, leaving a
; phantom install that the uninstaller cannot reclaim.
#define RuntimeVersion "3.13.15"
#define RuntimeSourceDir "..\..\runtime\dist\QuillVilleRuntime"
#define AppRefId "weather"

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
; installing this variant upgrades an existing Weather in place rather
; than sitting beside it.
AppId={{7B0C2E14-9A3D-4F6B-B1E2-8C5D3A9F0E21}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
VersionInfoVersion=2.2.0.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} accessible weather with alert monitoring (shared runtime)
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
OutputBaseFilename=Quill-Weather-Setup-Shared-{#AppVersion}
; Kept in step with quill-radio.iss (2026-08-17): 64-bit Setup (Inno 7) +
; 128 MB LZMA dictionary, which dedupes the embedded runtime's near-identical
; ffmpeg.exe/ffprobe.exe pair in the solid stream (-27 MB measured on Radio).
SetupArchitecture=x64
Compression=lzma2/ultra
LZMADictionarySize=131072
SolidCompression=yes
WizardStyle=modern
CloseApplications=force
RestartApplications=no
UninstallDisplayName={#AppName} {#AppVersion}
UninstallDisplayIcon={app}\quill-weather.ico
SetupIconFile=..\assets\quill-weather.ico
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
; the app cannot launch.
Name: "runtime"; Description: "Shared QuillVille runtime (Python) -- installed once, reused by every QuillVille app"; Types: full compact custom; Flags: fixed
Name: "main"; Description: "{#AppName} (required)"; Types: full compact custom; Flags: fixed
Name: "docs"; Description: "Documentation (User Guide, Release Notes, Product Requirements)"; Types: full custom

[Files]
; Weather's own payload is tiny: just its icon, the per-app C launcher
; (the portable-mode anchor), and (optionally) its docs. The program
; itself lives in the shared runtime, installed by the fragment below.
Source: "..\assets\quill-weather.ico"; DestDir: "{app}"; Components: main; Flags: ignoreversion
Source: "..\dist\QuillWeather\QuillWeather.exe"; DestDir: "{app}"; Components: main; Flags: ignoreversion
Source: "..\dist\QuillWeather\docs\*"; DestDir: "{app}\docs"; Components: docs; Flags: ignoreversion recursesubdirs createallsubdirs

; The shared runtime (install-if-absent) + reference registration + orphan
; removal on uninstall. Defines RuntimeDir/RuntimeExe used by [Icons]/[Run].
#include "..\..\..\installer\shared-runtime.iss"

[Icons]
; Every shortcut launches through the shared runtime. WorkingDir is the
; shared runtime dir so `python -m quill.apps.weather` finds the per-app
; quill package at the shared location's sitecustomize path.
Name: "{group}\{#AppName}"; Filename: "{code:RuntimeExe}"; Parameters: "-m quill.apps.weather"; WorkingDir: "{code:RuntimeDir}"; IconFilename: "{app}\quill-weather.ico"; Components: main
Name: "{group}\{#AppName} User Guide"; Filename: "{app}\docs\userguide.md"; Components: docs
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{code:RuntimeExe}"; Parameters: "-m quill.apps.weather"; WorkingDir: "{code:RuntimeDir}"; IconFilename: "{app}\quill-weather.ico"; Tasks: desktopicon; Components: main

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{code:RuntimeExe}"; Parameters: "-m quill.apps.weather"; Description: "Launch {#AppName}"; Flags: postinstall nowait skipifsilent unchecked

[UninstallDelete]
; Remove only Weather's own {app} payload. The shared runtime is left
; to the fragment's CurUninstallStepChanged, which deletes it only
; when unreferenced (no other QuillVille app still references the
; version that was registered at install time). The {app}\_internal
; tree that the old onedir layout used is gone in the shared layout.
Type: filesandordirs; Name: "{app}"

; Weather shares its saved-locations and settings store (%APPDATA%\Quill)
; with QUILL and the other apps; uninstall never touches that data.
; The full QUILL uninstaller owns that decision (it is the only
; uninstaller that knows the user's preferences).
