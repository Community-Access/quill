; Quill Converter installer -- shared-runtime layout (first release 1.0.0).
;
; Every shipping QuillVille product installs the shared QuillVille Runtime once
; (at %LOCALAPPDATA%\QuillVille\Runtime\) and launches through it. The
; install-if-absent and reference counting belong to
; installer\shared-runtime.iss; this script declares the identifiers the
; fragment needs (RuntimeVersion, RuntimeSourceDir, AppRefId, ToolFfmpeg) and
; includes it.
;
; Everything Quill Converter can use is inside this installer, so nothing
; downloads on first use: FFmpeg and ffprobe (staged into the runtime's
; tools\ffmpeg by build_release.ps1, because quill.apps.converter declares
; REQUIRED_COMPONENTS = ("ffmpeg",)), yt-dlp for Convert from URL and mutagen
; for cover art (both frozen into the runtime), and the OptiLab Core adapter
; when the build machine could compile it.
;
; The per-app payload is tiny: the icon, the per-app C launcher
; (QuillConverter.exe, the portable-mode anchor), the edition marker, and the
; rendered docs.
;
; Build inputs (must exist before ISCC runs):
;   - the shared runtime at ..\..\runtime\dist\QuillVilleRuntime, with
;     tools\ffmpeg staged;
;   - ..\dist\QuillConverter\QuillConverter.exe (build_native_launcher.py);
;   - ..\assets\quill-converter.ico;
;   - ..\dist\QuillConverter\docs (rendered by scripts\render_docs.ps1);
;   - explorer-verb.iss beside this file (generated from the format
;     catalogue by scripts\build_converter_verb_iss.py; a test keeps it in step).
;
; scripts\build_release.ps1 chains every step; running ISCC directly needs
; them all to exist already.

#define AppName "Quill Converter"
; Version is single-sourced from build_release.ps1 (/dAppVersion=<version>);
; the literal is the fallback for a manual ISCC run and must match it.
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppPublisher "Community Access"
#define AppURL "https://github.com/Community-Access/quill"

; -- shared runtime parameters (read by installer\shared-runtime.iss) ----------
; AppRefId is this app's stable key in runtime.state.json. It MUST stay
; "converter" forever -- renaming it would orphan the reference and leave a
; phantom install the uninstaller cannot reclaim.
#define RuntimeVersion "3.13.15"
#define RuntimeSourceDir "..\..\runtime\dist\QuillVilleRuntime"
#define AppRefId "converter"
; quill.apps.converter REQUIRED_COMPONENTS = ("ffmpeg",): the fragment packs
; tools\ffmpeg unconditionally, whatever order the family was installed in.
#define ToolFfmpeg
; ...and "mpv" (1.0.0): the Chapter Workbench's player, for exact seeking.
#define ToolMpv

[Setup]
#ifdef Sign
; Code signing (opt-in): present only when ISCC gets /DSign plus a matching
; /Squilltrusted=<sign command>. See docs/code-signing.md.
SignTool=quilltrusted
SignedUninstaller=yes
#endif
; A new AppId: Quill Converter has never shipped an installer before 1.0.0.
AppId={{43530606-3B45-4A97-A860-E21F4BF43117}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
VersionInfoVersion=1.0.0.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} accessible audio and video converter (shared runtime)
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
; The -Shared suffix is the name every QuillVille installer and the updater's
; asset matching share. Two downloads, as Radio and QUILL Lite publish: this
; installer and the portable zip.
OutputBaseFilename=Quill-Converter-Setup-Shared-{#AppVersion}
; 64-bit Setup (Inno Setup 7) so the LZMA dictionary can span ffmpeg.exe and
; ffprobe.exe, near-identical bytes a 32 MB dictionary cannot dedupe.
SetupArchitecture=x64
Compression=lzma2/ultra
LZMADictionarySize=131072
SolidCompression=yes
WizardStyle=modern
CloseApplications=force
RestartApplications=no
ChangesAssociations=yes
UninstallDisplayName={#AppName} {#AppVersion}
UninstallDisplayIcon={app}\quill-converter.ico
SetupIconFile=..\assets\quill-converter.ico
LicenseFile=..\LICENSE
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Types]
Name: "full"; Description: "Full installation (recommended)"
Name: "compact"; Description: "Compact installation (program only, no bundled documentation)"
Name: "custom"; Description: "Custom installation"; Flags: iscustom

[Components]
Name: "runtime"; Description: "Shared QuillVille runtime (Python and FFmpeg) -- installed once, reused by every QuillVille app"; Types: full compact custom; Flags: fixed
Name: "main"; Description: "{#AppName} (required)"; Types: full compact custom; Flags: fixed
Name: "docs"; Description: "Documentation (User Guide, Release Notes, Changelog, Product Requirements)"; Types: full custom

[Tasks]
Name: "explorerverb"; Description: "Add ""Convert with Quill Converter"" to the File Explorer right-click menu for audio and video files"; GroupDescription: "File Explorer:"
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "..\assets\quill-converter.ico"; DestDir: "{app}"; Components: main; Flags: ignoreversion
Source: "..\dist\QuillConverter\QuillConverter.exe"; DestDir: "{app}"; Components: main; Flags: ignoreversion
; Which edition this is, so Check for Updates offers THIS installer back.
Source: "..\installer\edition-installer-full.txt"; DestDir: "{app}"; DestName: "quill-edition.txt"; Components: main; Flags: ignoreversion
Source: "..\dist\QuillConverter\docs\*"; DestDir: "{app}\docs"; Components: docs; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "*.epub"

; The Explorer verb: one key per audio/video extension, per user (HKCU), and
; removed by the uninstaller. Generated; do not edit by hand.
#include "explorer-verb.iss"

; The shared runtime (install-if-absent) + reference registration + orphan
; removal on uninstall. Defines RuntimeDir/RuntimeExe used below. It ends in a
; [Code] section, so every other section include must come before it.
#include "..\..\..\installer\shared-runtime.iss"

[Icons]
; Every shortcut launches through {app}\QuillConverter.exe, the native
; launcher, which resolves the shared runtime and runs -m quill.apps.converter.
Name: "{group}\{#AppName}"; Filename: "{app}\QuillConverter.exe"; IconFilename: "{app}\quill-converter.ico"; Components: main
Name: "{group}\{#AppName} User Guide"; Filename: "{app}\docs\userguide.html"; Components: docs
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\QuillConverter.exe"; IconFilename: "{app}\quill-converter.ico"; Tasks: desktopicon; Components: main

[Run]
Filename: "{app}\QuillConverter.exe"; Description: "Launch {#AppName}"; Flags: postinstall nowait skipifsilent unchecked

[UninstallDelete]
; Only the Converter's own {app} payload. The shared runtime is the
; fragment's to remove, and only when no other QuillVille app references it.
; Settings (converter.json in %APPDATA%\Quill) are shared with the family and
; are never touched here.
Type: filesandordirs; Name: "{app}"
