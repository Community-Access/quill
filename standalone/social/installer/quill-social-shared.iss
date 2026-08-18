; QUILL Social installer -- shared-runtime layout.
;
; Promoted from the onedir layout to the shared QuillVille Runtime
; (2026-08-18). See standalone\radio\installer\quill-radio.iss for the full
; rationale. Social's application package (quill_social) ships INSIDE the
; shared runtime -- the runtime spec has collected it since the design
; landed, and the quill-social wheel declared in pyproject [runtime] finally
; makes that collection real -- so the per-app payload is just the launcher,
; the icon, and docs, launched via `{code:RuntimeExe} -m quill_social`.
; Social declares no media components; its build strips any staged
; ffmpeg/mpv from the runtime payload before this compiles.
;
; Build inputs (must exist before ISCC runs):
;   - the shared runtime at ..\..\runtime\dist\QuillVilleRuntime, built from
;     an environment with quill-social installed (check_runtime_imports
;     probes it);
;   - the per-app QuillSocial.exe at ..\dist\QuillSocial-shared\QuillSocial.exe
;     (built by scripts\build_native_launcher.py --product social);
;   - the rendered Social docs at ..\dist\QuillSocial-shared\docs.

#define AppName "QUILL Social"
#ifndef AppVersion
  #define AppVersion "0.3.0"
#endif
#define AppPublisher "Community Access"
#define AppURL "https://github.com/Community-Access/quill"

; -- shared runtime parameters (read by installer\shared-runtime.iss) ----------
; AppRefId MUST stay "social" forever; renaming orphans the reference.
#define RuntimeVersion "3.13.15"
#define RuntimeSourceDir "..\..\runtime\dist\QuillVilleRuntime"
#define AppRefId "social"

[Setup]
#ifdef Sign
SignTool=quilltrusted
SignedUninstaller=yes
#endif
; Same AppId as the legacy onedir installer: same product, so this variant
; upgrades an existing self-contained Social in place.
AppId={{76E44E58-70E4-492C-ACAE-B59BE03C94DC}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} accessible social reading and publishing (shared runtime)
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
OutputBaseFilename=QUILL-Social-Setup-Shared-{#AppVersion}
SetupArchitecture=x64
Compression=lzma2/ultra
LZMADictionarySize=131072
SolidCompression=yes
WizardStyle=modern
CloseApplications=force
RestartApplications=no
UninstallDisplayName={#AppName} {#AppVersion}
UninstallDisplayIcon={app}\quill-social.ico
SetupIconFile=..\assets\quill-social.ico
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
Source: "..\assets\quill-social.ico"; DestDir: "{app}"; Components: main; Flags: ignoreversion
Source: "..\dist\QuillSocial-shared\QuillSocial.exe"; DestDir: "{app}"; Components: main; Flags: ignoreversion
Source: "..\installer\edition-installer-full.txt"; DestDir: "{app}"; DestName: "quill-edition.txt"; Components: main; Flags: ignoreversion
Source: "..\dist\QuillSocial-shared\docs\*"; DestDir: "{app}\docs"; Components: docs; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

#include "..\..\..\installer\shared-runtime.iss"

[Icons]
Name: "{group}\{#AppName}"; Filename: "{code:RuntimeExe}"; Parameters: "-m quill_social"; WorkingDir: "{code:RuntimeDir}"; IconFilename: "{app}\quill-social.ico"; Components: main
Name: "{group}\{#AppName} User Guide"; Filename: "{app}\docs\userguide.md"; Components: docs
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{code:RuntimeExe}"; Parameters: "-m quill_social"; WorkingDir: "{code:RuntimeDir}"; IconFilename: "{app}\quill-social.ico"; Tasks: desktopicon; Components: main

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{code:RuntimeExe}"; Parameters: "-m quill_social"; Description: "Launch {#AppName}"; Flags: postinstall nowait skipifsilent unchecked

[UninstallDelete]
; Only Social's own payload; the shared runtime is refcounted by the
; fragment, and the local store (accounts, drafts, folders) is never touched.
Type: filesandordirs; Name: "{app}"
