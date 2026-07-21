; QUILL Social installer -- ships the staged onedir build.
; Compile via scripts\build_release.ps1 (which renders + stages docs into
; ..\dist\QuillSocial first), or directly:  ISCC quill-social.iss
;
; Everything the app needs is bundled -- no downloads at install or runtime.
; The staged folder deliberately contains NO data\ subfolder here: that folder
; is the portable-mode switch (see the portable zip and launcher.py), and an
; installed copy keeps using the platform app-data / shared %APPDATA%\Quill store.

#define AppName "QUILL Social"
; Version is single-sourced from build_release.ps1, which passes
; /dAppVersion=<version> to ISCC. The literal below is only the fallback for a
; manual ISCC run and must be kept in step with build_release.ps1's $version.
#ifndef AppVersion
  #define AppVersion "0.3.0"
#endif
#define AppPublisher "Community Access"
#define AppURL "https://github.com/Community-Access/quill-social"
#define AppExeName "QuillSocial.exe"

[Setup]
AppId={{76E44E58-70E4-492C-ACAE-B59BE03C94DC}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} accessible social networking
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
OutputBaseFilename=QUILL-Social-Setup-{#AppVersion}
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
CloseApplications=force
RestartApplications=no
UninstallDisplayName={#AppName} {#AppVersion}
UninstallDisplayIcon={app}\{#AppExeName}
LicenseFile=..\LICENSE
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[InstallDelete]
; Upgrade hygiene: the onedir layout's _internal tree is wholly ours; wipe it
; before [Files] re-lays it so renamed/removed modules never linger and cause
; version-skew import errors on upgrade.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\dist\QuillSocial\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "data\*"

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{group}\{#AppName} User Guide"; Filename: "{app}\docs\USER_GUIDE.md"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: postinstall nowait skipifsilent unchecked

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_internal"

; Deliberately NO data-wipe prompt on uninstall: QUILL Social's local store
; may live in the shared %APPDATA%\Quill area alongside its sibling apps.
; Removing this app must never destroy data a sibling still uses; the full
; QUILL uninstaller owns that decision.
