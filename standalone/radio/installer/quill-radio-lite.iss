; Quill Radio -- THIN ("-Lite") installer.
;
; Ships ONLY the tiny native launcher + docs. It does NOT bundle the ~230 MB
; shared QuillVille Runtime; if the runtime is not already installed it
; downloads and runs the standalone QuillVille Runtime installer (a GitHub
; release asset), showing Inno Setup's built-in ACCESSIBLE download progress
; page (a standard progress bar + status text that NVDA/JAWS/Narrator read).
; Every QuillVille app reuses that one runtime. Same AppId as the full/shared
; installer, so either one upgrades the other. Requires Inno Setup 6.1+.

#define AppName "Quill Radio"
#ifndef AppVersion
  #define AppVersion "3.0.0"
#endif
#define AppPublisher "Community Access"
#define AppURL "https://github.com/Community-Access/quill-radio"
#define RuntimeUrl "https://github.com/Community-Access/quill/releases/latest/download/QuillVille-Runtime-Setup.exe"

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
AppId={{35DAB52F-94BB-475C-BA97-A5059C85B3D1}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
VersionInfoVersion=3.0.0.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} (thin installer -- shared runtime downloaded on demand)
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=auto
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputBaseFilename=Quill-Radio-Lite-Setup-{#AppVersion}
; 64-bit Setup for parity with the full installer (and high-entropy ASLR).
; Deliberately NO enlarged LZMADictionarySize here: the payload is ~3 MB, and
; a large dictionary is a buffer the end user's machine must allocate during
; install for no compression gain at this size.
SetupArchitecture=x64
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
CloseApplications=force
UninstallDisplayName={#AppName} {#AppVersion} (Lite)
UninstallDisplayIcon={app}\quill-radio.ico
SetupIconFile=..\assets\quill-radio.ico
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\assets\quill-radio.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\QuillRadio\QuillRadio.exe"; DestDir: "{app}"; Flags: ignoreversion
; See quill-radio.iss: the updater reads this to offer the right edition.
Source: "..\installer\edition-installer-lite.txt"; DestDir: "{app}"; DestName: "quill-edition.txt"; Flags: ignoreversion
Source: "..\dist\QuillRadio\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\QuillRadio.exe"; IconFilename: "{app}\quill-radio.ico"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\QuillRadio.exe"; IconFilename: "{app}\quill-radio.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{app}\QuillRadio.exe"; Description: "Launch {#AppName}"; Flags: postinstall nowait skipifsilent unchecked

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
var
  DownloadPage: TDownloadWizardPage;

function RuntimeMissing(): Boolean;
begin
  Result := not FileExists(
    ExpandConstant('{localappdata}\QuillVille\Runtime\3.13\quillville-runtime.json'));
end;

function OnDownloadProgress(const Url, FileName: String; const Progress, ProgressMax: Int64): Boolean;
begin
  Result := True;
end;

procedure InitializeWizard;
begin
  DownloadPage := CreateDownloadPage(
    'Preparing the QuillVille Runtime',
    'Quill Radio runs on the shared QuillVille Runtime. If it is not already ' +
    'installed, it will be downloaded now (about 230 MB, once) -- every ' +
    'QuillVille app reuses it afterward.',
    @OnDownloadProgress);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ResultCode: Integer;
  RuntimeSetup: String;
begin
  Result := True;
  if (CurPageID = wpReady) and RuntimeMissing() then
  begin
    DownloadPage.Clear;
    DownloadPage.Add('{#RuntimeUrl}', 'QuillVille-Runtime-Setup.exe', '');
    DownloadPage.Show;
    try
      try
        DownloadPage.Download;
      except
        if DownloadPage.AbortedByUser then
          MsgBox('The runtime download was cancelled. Quill Radio will ' +
                 'offer to download it again the first time you launch it.', mbInformation, MB_OK)
        else
          MsgBox('The QuillVille Runtime could not be downloaded: ' + GetExceptionMessage + #13#10#13#10 +
                 'You can install it later; Quill Radio will ' +
                 'offer to download it on first launch.', mbError, MB_OK);
        DownloadPage.Hide;
        Exit;
      end;
      RuntimeSetup := ExpandConstant('{tmp}\QuillVille-Runtime-Setup.exe');
      Exec(RuntimeSetup, '', '', SW_SHOWNORMAL, ewWaitUntilTerminated, ResultCode);
    finally
      DownloadPage.Hide;
    end;
  end;
end;
