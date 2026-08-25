; QUILL Cast installer -- ships the staged onedir build.
; Compile via scripts\build_release.ps1 (which stages ffmpeg/docs into
; ..\dist\QUILLCast first), or directly:  ISCC quill-cast.iss
;
; Everything the app needs is bundled -- no downloads at install or runtime.
; The staged folder deliberately contains NO data\ subfolder here: that
; folder is the portable-mode switch (see the portable zip), and an
; installed copy must keep using the shared %APPDATA%\Quill store.

#define AppName "QUILL Cast"
; Version is single-sourced from build_release.ps1, which passes
; /dAppVersion=<version> to ISCC. The literal below is only the fallback for a
; manual ISCC run and must be kept in step with build_release.ps1's $version.
; It was an unguarded #define pinned at 1.0.5, so a 1.0.7 build shipped a
; portable zip named 1.0.7 next to a Setup.exe that called itself 1.0.5.
#ifndef AppVersion
  #define AppVersion "2.0.0"
#endif
#define AppPublisher "Community Access"
#define AppURL "https://github.com/Community-Access/quill-cast"
#define AppExeName "QUILLCast.exe"

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
AppId={{316B5D30-E16B-4973-95B6-968F5D897FD7}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
VersionInfoVersion=2.0.0.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} accessible podcast player
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
OutputBaseFilename=QUILL-Cast-Setup-{#AppVersion}
; 64-bit Setup (Inno 7) + 128 MB LZMA dictionary: the payload embeds the
; near-identical ffmpeg/ffprobe pair, which only a large dictionary can
; dedupe in the solid stream (-27 MB measured on Quill Radio, 2026-08-17).
SetupArchitecture=x64
Compression=lzma2/ultra
LZMADictionarySize=131072
SolidCompression=yes
WizardStyle=modern
CloseApplications=force
RestartApplications=no
UninstallDisplayName={#AppName} {#AppVersion}
UninstallDisplayIcon={app}\{#AppExeName}
SetupIconFile=..\assets\quill-cast.ico
LicenseFile=..\LICENSE
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Types]
Name: "full"; Description: "Full installation (recommended)"
Name: "compact"; Description: "Compact installation (program only, no bundled documentation)"
Name: "custom"; Description: "Custom installation"; Flags: iscustom

[Components]
Name: "main"; Description: "{#AppName} (required)"; Types: full compact custom; Flags: fixed
Name: "docs"; Description: "Documentation (User Guide)"; Types: full custom

[InstallDelete]
; Upgrade hygiene: the onedir layout's _internal tree is wholly ours; wipe it
; before [Files] re-lays it so renamed/removed modules never linger and cause
; version-skew import errors on upgrade.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\dist\QUILLCast\*"; DestDir: "{app}"; Components: main; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "data\*,docs\*"
Source: "..\dist\QUILLCast\docs\*"; DestDir: "{app}\docs"; Components: docs; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{group}\{#AppName} User Guide"; Filename: "{app}\docs\userguide.md"; Components: docs
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked
; Opt-in, and unchecked: taking over a file type without being asked is how an
; installer earns a reputation. Somebody who exported a subscription list from
; another podcast app can then open it the way they open anything else.
Name: "opmlassoc"; Description: "Open &subscription lists (.opml) with {#AppName}"; GroupDescription: "File types:"; Flags: unchecked

[Registry]
; The .opml association, written under HKA so it follows the install scope --
; per-user for the default lowest-privileges install, machine-wide when the
; user elevated. uninsdeletekey/uninsdeletevalue means uninstalling gives the
; extension back rather than leaving a dead handler behind.
;
; Deliberately NOT the ".xml" extension, though the app accepts one on the
; command line: .xml belongs to no single application and claiming it would
; break unrelated files. A .xml subscription list still imports fine through
; Import OPML... or by dragging it onto the app.
Root: HKA; Subkey: "Software\Classes\.opml"; ValueType: string; ValueName: ""; ValueData: "QUILLCast.opml"; Flags: uninsdeletevalue; Tasks: opmlassoc
Root: HKA; Subkey: "Software\Classes\QUILLCast.opml"; ValueType: string; ValueName: ""; ValueData: "Podcast subscription list"; Flags: uninsdeletekey; Tasks: opmlassoc
Root: HKA; Subkey: "Software\Classes\QUILLCast.opml\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExeName},0"; Tasks: opmlassoc
Root: HKA; Subkey: "Software\Classes\QUILLCast.opml\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""; Tasks: opmlassoc
; Listed in Explorer's "Open with" for .opml even when it is not the default,
; so a file that belongs to another app can still be sent here once.
Root: HKA; Subkey: "Software\Classes\.opml\OpenWithProgids"; ValueType: string; ValueName: "QUILLCast.opml"; ValueData: ""; Flags: uninsdeletevalue; Tasks: opmlassoc

; The quill-cast:// URI scheme, for "Share This Moment" links -- a link that
; reopens an episode at the second it was shared from. Written unconditionally
; rather than behind a task: a scheme nobody else claims is not a file type
; being taken over, and a shared link that does nothing is the failure the
; feature exists to avoid. "URL Protocol" (empty value) is what marks the key
; as a protocol handler; Windows requires it to be present, not to have a value.
;
; The app never fetches what the link names. It resolves to a feed address and
; a GUID, looks both up in the library the listener already subscribes to, and
; does nothing at all if they are not there -- see core/podcasts/share_links.
Root: HKA; Subkey: "Software\Classes\quill-cast"; ValueType: string; ValueName: ""; ValueData: "URL:QUILL Cast episode"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\quill-cast"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""
Root: HKA; Subkey: "Software\Classes\quill-cast\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExeName},0"
Root: HKA; Subkey: "Software\Classes\quill-cast\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: postinstall nowait skipifsilent unchecked

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_internal"

; Deliberately NO data-wipe prompt on uninstall: QUILL Cast shares its
; settings, subscriptions, and downloads store (%APPDATA%\Quill) with QUILL
; and Quill Radio. Removing this app must never destroy data a sibling app
; still uses; the full QUILL uninstaller owns that decision.
