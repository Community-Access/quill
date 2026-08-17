; Quill Radio installer -- SHARED-RUNTIME variant.
;
; Unlike quill-radio.iss (which ships Radio's own PyInstaller onedir with a
; private Python), this installs the shared QuillVille Runtime once and launches
; Radio through it (QuillVilleRuntime.exe -m quill.apps.radio). A second
; QuillVille app reuses the same runtime instead of installing another Python
; (installer\shared-runtime.iss does the install-if-absent + reference counting).
;
; Build inputs (produce before ISCC):
;   - the shared runtime at ..\..\runtime\dist\QuillVilleRuntime (built by
;     ..\..\runtime\quillville-runtime.spec, marker stamped, ffmpeg/mpv staged
;     into its tools\ so Radio finds them via QUILL_APP_ROOT);
;   - Radio's rendered docs in ..\docs (render_docs.ps1).
;
; STATUS: authored for validation. The proven onedir quill-radio.iss remains the
; shipping installer until this variant passes a Windows install/uninstall test
; (shared runtime installs once, a second app skips it, uninstall removes it only
; when the last app is gone), then it is promoted to the default.

#define AppName "Quill Radio"
#ifndef AppVersion
  #define AppVersion "3.0.0"
#endif
#define AppPublisher "Community Access"
#define AppURL "https://github.com/Community-Access/quill-radio"

; -- shared runtime parameters (read by installer\shared-runtime.iss) ----------
#define RuntimeVersion "3.13.15"
#define RuntimeSourceDir "..\..\runtime\dist\QuillVilleRuntime"
#define AppRefId "radio"

[Setup]
; Same AppId as the onedir installer: it is the same product, so installing this
; variant upgrades an existing Radio in place rather than sitting beside it.
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
OutputBaseFilename=Quill-Radio-Setup-Shared-{#AppVersion}
; Kept in step with quill-radio.iss: 64-bit Setup + 128 MB dictionary to
; dedupe ffmpeg/ffprobe in the solid stream (-27 MB, measured 2026-08-17).
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
Name: "runtime"; Description: "Shared QuillVille runtime (Python) -- installed once, reused by every QuillVille app"; Types: full compact custom; Flags: fixed
Name: "main"; Description: "{#AppName} (required)"; Types: full compact custom; Flags: fixed
Name: "docs"; Description: "Documentation (User Guide, Release Notes, Product Requirements)"; Types: full custom

[Files]
; Radio's own payload is tiny: just its icon and (optionally) its docs. The
; program itself lives in the shared runtime, installed by the fragment below.
Source: "..\assets\quill-radio.ico"; DestDir: "{app}"; Components: main; Flags: ignoreversion
Source: "..\docs\*"; DestDir: "{app}\docs"; Components: docs; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "*.epub"

; The shared runtime (install-if-absent) + reference registration + orphan
; removal on uninstall. Defines RuntimeDir/RuntimeExe used by [Icons]/[Run].
#include "..\..\..\installer\shared-runtime.iss"

[Icons]
Name: "{group}\{#AppName}"; Filename: "{code:RuntimeExe}"; Parameters: "-m quill.apps.radio"; WorkingDir: "{code:RuntimeDir}"; IconFilename: "{app}\quill-radio.ico"; Components: main
Name: "{group}\{#AppName} User Guide"; Filename: "{app}\docs\userguide.md"; Components: docs
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{code:RuntimeExe}"; Parameters: "-m quill.apps.radio"; WorkingDir: "{code:RuntimeDir}"; IconFilename: "{app}\quill-radio.ico"; Tasks: desktopicon; Components: main

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{code:RuntimeExe}"; Parameters: "-m quill.apps.radio"; Description: "Launch {#AppName}"; Flags: postinstall nowait skipifsilent unchecked

[UninstallDelete]
; Remove only Radio's own {app} payload. The shared runtime is left to the
; fragment's CurUninstallStepChanged, which deletes it only when unreferenced.
Type: filesandordirs; Name: "{app}"

; Radio shares its settings/favorites/recordings store (%APPDATA%\Quill) with
; QUILL and the other apps; uninstall never touches that data.
