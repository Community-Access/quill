; QuillLite -- THIN ("-Lite") installer.
;
; Ships ONLY the tiny native launcher + docs. It does NOT bundle the shared
; QuillVille Runtime; if the runtime is not already installed it downloads and
; runs the standalone QuillVille Runtime installer (a GitHub release asset),
; showing Inno Setup's built-in ACCESSIBLE download progress page (a standard
; progress bar + status text that NVDA/JAWS/Narrator read). Every QuillVille app
; reuses that one runtime. Same AppId as the shared installer, so either one
; upgrades the other. Requires Inno Setup 6.1+.
; Cloned from standalone\inkwell\installer\quill-inkwell-lite.iss.
;
; The product half of the name is the mixed-case "QuillLite" -- one word, so a
; screen reader speaks it as a name rather than spelling out hyphens (Jeff,
; 2026-09-08). "-Lite-Setup" after it is the family's name for the thin
; installer flavour, not for the product.

#define AppName "QuillLite"
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppPublisher "Community Access"
#define AppURL "https://github.com/Community-Access/quill"
#define RuntimeUrl "https://github.com/Community-Access/quill/releases/download/runtime-latest/QuillVille-Runtime-Setup.exe"

[Setup]
#ifdef Sign
SignTool=quilltrusted
SignedUninstaller=yes
#endif
AppId={{3F1B6C08-2D47-4A19-9E63-5C7A08B41D22}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} (thin installer -- shared runtime downloaded on demand)
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=auto
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputBaseFilename=QuillLite-Lite-Setup-{#AppVersion}
; Deliberately NO enlarged LZMADictionarySize: the payload is a few MB, and a
; large dictionary is a buffer the user's machine must allocate for no gain.
SetupArchitecture=x64
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
CloseApplications=force
UninstallDisplayName={#AppName} {#AppVersion} (Lite)
UninstallDisplayIcon={app}\quill-lite.ico
SetupIconFile=..\assets\quill-lite.ico
LicenseFile=..\LICENSE
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\assets\quill-lite.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\QuillLite-shared\QuillLite.exe"; DestDir: "{app}"; Flags: ignoreversion
; The updater reads this to offer the right edition back (core/install_edition.py).
Source: "..\installer\edition-installer-lite.txt"; DestDir: "{app}"; DestName: "quill-edition.txt"; Flags: ignoreversion
Source: "..\dist\QuillLite-shared\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\QuillLite.exe"; IconFilename: "{app}\quill-lite.ico"
Name: "{group}\{#AppName} User Guide"; Filename: "{app}\docs\userguide.html"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\QuillLite.exe"; IconFilename: "{app}\quill-lite.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{app}\QuillLite.exe"; Description: "Launch {#AppName}"; Flags: postinstall nowait skipifsilent unchecked

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
    'QuillLite runs on the shared QuillVille Runtime. If it is not already ' +
    'installed, it will be downloaded now (about 150 MB, once) -- every ' +
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
          MsgBox('The runtime download was cancelled. QuillLite will ' +
                 'offer to download it again the first time you launch it.', mbInformation, MB_OK)
        else
          MsgBox('The QuillVille Runtime could not be downloaded: ' + GetExceptionMessage + #13#10#13#10 +
                 'You can install it later; QuillLite will ' +
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
