; QUILL Audio Studio installer -- shared-runtime layout.
;
; Promoted from the onedir layout to the shared QuillVille Runtime
; (2026-07-24). See standalone\radio\installer\quill-radio.iss for the
; full rationale; Audio Studio follows the same pattern (per-app C
; launcher + docs only; the program itself lives in the shared runtime,
; launched via `{code:RuntimeExe} -m quill.apps.studio`). ffmpeg and
; the mpv engine are bundled into the shared runtime's tools\ by
; standalone\runtime\build_runtime.ps1 -- the per-app install no
; longer needs them.
;
; Build inputs (must exist before ISCC runs):
;   - the shared runtime at ..\..\runtime\dist\QuillVilleRuntime
;     (built by ..\..\runtime\quillville-runtime.spec, marker stamped,
;     ffmpeg/mpv staged into its tools\ so Studio finds them via
;     QUILL_APP_ROOT);
;   - the per-app QuillAudioStudio.exe at
;     ..\dist\QuillAudioStudio\QuillAudioStudio.exe (built by
;     build_native_launcher.py);
;   - the per-app icon at ..\assets\quill-audio-studio.ico;
;   - the rendered Studio docs at ..\dist\QuillAudioStudio\docs.

#define AppName "QUILL Audio Studio"
; Version is single-sourced from build_release.ps1, which passes
; /dAppVersion=<version> to ISCC. The literal below is only the fallback for a
; manual ISCC run and must be kept in step with build_release.ps1's $version.
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppPublisher "Community Access"
#define AppURL "https://github.com/Community-Access/quill-audio-studio"

; -- shared runtime parameters (read by installer\shared-runtime.iss) ----------
; AppRefId is the stable per-app key the fragment uses in
; runtime.state.json. It MUST stay "studio" forever -- renaming it
; would orphan the previous reference and double-count, leaving a
; phantom install that the uninstaller cannot reclaim.
#define RuntimeVersion "3.13.15"
#define RuntimeSourceDir "..\..\runtime\dist\QuillVilleRuntime"
#define AppRefId "studio"
; quill.apps.studio REQUIRED_COMPONENTS = ("ffmpeg", "mpv") -- mpv for the
; player preview this build has always bundled.
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
; installing this variant upgrades an existing Audio Studio in place
; rather than sitting beside it.
AppId={{64D6B5F9-01E3-47D5-B49F-794DFC0106BF}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
VersionInfoVersion=1.0.0.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} accessible audio production studio (shared runtime)
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
; The -Shared suffix matches the per-app pattern; drop once the
; shared-runtime install is the only shipping layout.
#ifdef Offline
; The Offline Edition: build_release.ps1 -Offline stages the whisper.cpp
; engine and a starter model into the runtime payload before ISCC runs
; (scripts\stage_offline_speech.py), so this flavor dictates with zero
; network access -- and, because the runtime is shared, so does every other
; QuillVille app on the machine.
OutputBaseFilename=QUILL-Audio-Studio-Offline-Setup-{#AppVersion}
#else
OutputBaseFilename=QUILL-Audio-Studio-Setup-Shared-{#AppVersion}
#endif
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
UninstallDisplayIcon={app}\quill-audio-studio.ico
SetupIconFile=..\assets\quill-audio-studio.ico
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
; the app cannot launch. ffmpeg and the mpv engine are part of the
; shared runtime's payload, installed by the fragment below.
Name: "runtime"; Description: "Shared QuillVille runtime (Python) -- installed once, reused by every QuillVille app"; Types: full compact custom; Flags: fixed
Name: "main"; Description: "{#AppName} (required)"; Types: full compact custom; Flags: fixed
Name: "docs"; Description: "Documentation (User Guide)"; Types: full custom

[Files]
; Audio Studio's own payload is tiny: just its icon, the per-app C
; launcher (the portable-mode anchor), and (optionally) its docs.
; The program itself lives in the shared runtime, installed by the
; fragment below. ffmpeg.exe / libmpv-2.dll are part of the shared
; runtime's tools\, not {app}, so they are not listed here.
Source: "..\assets\quill-audio-studio.ico"; DestDir: "{app}"; Components: main; Flags: ignoreversion
Source: "..\dist\QuillAudioStudio\QuillAudioStudio.exe"; DestDir: "{app}"; Components: main; Flags: ignoreversion
Source: "..\dist\QuillAudioStudio\docs\*"; DestDir: "{app}\docs"; Components: docs; Flags: ignoreversion recursesubdirs createallsubdirs

; The shared runtime (install-if-absent) + reference registration + orphan
; removal on uninstall. Defines RuntimeDir/RuntimeExe used by [Icons]/[Run].
#include "..\..\..\installer\shared-runtime.iss"

[Icons]
; Every shortcut launches through the shared runtime. WorkingDir is the
; shared runtime dir so `python -m quill.apps.studio` finds the per-app
; quill package at the shared location's sitecustomize path.
Name: "{group}\{#AppName}"; Filename: "{code:RuntimeExe}"; Parameters: "-m quill.apps.studio"; WorkingDir: "{code:RuntimeDir}"; IconFilename: "{app}\quill-audio-studio.ico"; Components: main
Name: "{group}\{#AppName} User Guide"; Filename: "{app}\docs\userguide.md"; Components: docs
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{code:RuntimeExe}"; Parameters: "-m quill.apps.studio"; WorkingDir: "{code:RuntimeDir}"; IconFilename: "{app}\quill-audio-studio.ico"; Tasks: desktopicon; Components: main

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{code:RuntimeExe}"; Parameters: "-m quill.apps.studio"; Description: "Launch {#AppName}"; Flags: postinstall nowait skipifsilent unchecked

[UninstallDelete]
; Remove only Audio Studio's own {app} payload. The shared runtime is
; left to the fragment's CurUninstallStepChanged, which deletes it
; only when unreferenced. The {app}\_internal tree that the old onedir
; layout used is gone in the shared layout.
Type: filesandordirs; Name: "{app}"

; Audio Studio shares its settings, library, and recordings store
; (%APPDATA%\Quill) with QUILL and the other apps; uninstall never
; touches that data. The full QUILL uninstaller owns that decision.
