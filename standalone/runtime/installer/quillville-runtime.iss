; The standalone QuillVille Runtime installer -- QuillVille-Runtime-Setup.exe.
;
; This is the asset every "-Lite" app installer (Radio, Weather, Studio)
; downloads from the latest GitHub release when the shared runtime is not
; already installed, and the asset an app offers to fetch on first launch if
; the user declined it at install time. Until 2026-08-18 NOTHING built this
; file and no release carried it, so every Lite install's runtime download
; failed. Compile via build_runtime_installer.ps1, which requires a built,
; gate-passing runtime in ..\dist\QuillVilleRuntime and derives AppVersion
; from its quillville-runtime.json marker.
;
; It installs the BASE runtime only -- no ffmpeg, no libmpv. The media apps'
; full installers carry those themselves (scripts\StageMediaTools.ps1), and a
; Lite install offers them as verified on-demand downloads. Bundling them here
; would make a Weather Lite user download 300 MB of media tools to read a
; forecast.
;
; Per-user on purpose: the runtime lives in {localappdata} and every
; QuillVille app on the machine reuses it, so no elevation is ever needed.

#define AppName "QuillVille Runtime"
; The release-channel slot this installer fills (build_runtime_installer.ps1
; -Channel beta passes /dRuntimeSlot=3.13-beta). Stable is the folder that
; always existed; the app installers' fragment uses the same names.
#ifndef RuntimeSlot
  #define RuntimeSlot "3.13"
#endif
#ifndef AppVersion
  #define AppVersion "3.13"
#endif
#define AppPublisher "Community Access"
#define AppURL "https://github.com/Community-Access/quill"

[Setup]
#ifdef Sign
; Code signing (opt-in). Present only when ISCC is invoked with /DSign plus a
; matching /Squilltrusted=<sign command>; see docs/code-signing.md.
SignTool=quilltrusted
SignedUninstaller=yes
#endif
#if RuntimeSlot == "3.13"
AppId={{6D6B0E7C-51A4-4B5E-9E0D-2F8B4C0A9137}}
#else
; A channel slot's runtime (build_runtime_installer.ps1 -Channel beta): its own
; AppId, so installing it never replaces the Stable runtime's uninstall entry.
AppId={{6D6B0E7C-51A4-4B5E-9E0D-2F8B4C0A9138}}
#endif
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription=Shared Python runtime for the QuillVille apps
; Runtime\3.13 for Stable, Runtime\3.13-beta for the Beta slot.
DefaultDirName={localappdata}\QuillVille\Runtime\{#RuntimeSlot}
; The path IS the contract (quill.core.runtime_marker and every per-app
; launcher resolve it); letting a user relocate it would strand every app.
DisableDirPage=yes
DisableProgramGroupPage=yes
; No Start Menu entry: the runtime is not a program a person launches.
CreateAppDir=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputBaseFilename=QuillVille-Runtime-Setup
; 64-bit Setup (Inno 7) + 128 MB LZMA dictionary, matching the app installers
; (see quill-radio.iss for the measurement that justified it).
SetupArchitecture=x64
Compression=lzma2/ultra
LZMADictionarySize=131072
SolidCompression=yes
WizardStyle=modern
; Apps hold the runtime open while running; force-close beats a locked-file
; retry loop a screen-reader user has to fight through.
CloseApplications=force
UninstallDisplayName={#AppName} {#AppVersion}
SetupIconFile=..\assets\quillville-runtime.ico
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\dist\QuillVilleRuntime\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
