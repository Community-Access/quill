; QUILL Audio Studio -- THIN ("-Lite") installer.
;
; Ships ONLY the tiny native launcher + docs (a few MB). It does NOT bundle the
; ~230 MB shared QuillVille Runtime. If the runtime is not already installed, the
; installer downloads and runs the standalone QuillVille Runtime installer from
; its GitHub release asset, showing Inno Setup's built-in ACCESSIBLE download
; progress page (a standard progress bar + status text that NVDA/JAWS/Narrator
; read, announced as a percentage). Every QuillVille app reuses that one runtime,
; so a user who already has it installed downloads only these few MB.
;
; This is the companion to the full "-Setup-Shared" installer (which bundles the
; runtime for offline installs). Same AppId, so either one upgrades the other.
;
; Build inputs:
;   - ..\dist\QuillAudioStudio\QuillAudioStudio.exe (the native launcher)
;   - ..\assets\quill-audio-studio.ico
;   - ..\dist\QuillAudioStudio\docs (rendered docs)
; Requires Inno Setup 6.1+ (for CreateDownloadPage).

#define AppName "QUILL Audio Studio"
#ifndef AppVersion
  #define AppVersion "2.2.0"
#endif
#define AppPublisher "Community Access"
#define AppURL "https://github.com/Community-Access/quill-audio-studio"
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
; Same AppId as the full/shared installer: this is the same product.
AppId={{64D6B5F9-01E3-47D5-B49F-794DFC0106BF}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
VersionInfoVersion=2.2.0.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} (thin installer -- shared runtime downloaded on demand)
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=auto
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputBaseFilename=QUILL-Audio-Studio-Lite-Setup-{#AppVersion}
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
CloseApplications=force
UninstallDisplayName={#AppName} {#AppVersion} (Lite)
UninstallDisplayIcon={app}\quill-audio-studio.ico
SetupIconFile=..\assets\quill-audio-studio.ico
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\assets\quill-audio-studio.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\QuillAudioStudio\QuillAudioStudio.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\QuillAudioStudio\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

[Icons]
; Launch through the native launcher, which resolves the shared runtime.
Name: "{group}\{#AppName}"; Filename: "{app}\QuillAudioStudio.exe"; IconFilename: "{app}\quill-audio-studio.ico"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\QuillAudioStudio.exe"; IconFilename: "{app}\quill-audio-studio.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{app}\QuillAudioStudio.exe"; Description: "Launch {#AppName}"; Flags: postinstall nowait skipifsilent unchecked

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
var
  DownloadPage: TDownloadWizardPage;

// True when the shared runtime's version marker is absent -- i.e. no QuillVille
// app has installed the runtime yet. Matches the launcher's location
// (%LOCALAPPDATA%\QuillVille\Runtime).
function RuntimeMissing(): Boolean;
begin
  Result := not FileExists(
    ExpandConstant('{localappdata}\QuillVille\Runtime\3.13\quillville-runtime.json'));
end;

function OnDownloadProgress(const Url, FileName: String; const Progress, ProgressMax: Int64): Boolean;
begin
  // Returning True keeps the (accessible) progress page updating. The page's
  // progress bar and status label are standard Win32 controls that screen
  // readers announce; Inno also updates them with the byte counts.
  Result := True;
end;

procedure InitializeWizard;
begin
  DownloadPage := CreateDownloadPage(
    'Preparing the QuillVille Runtime',
    'QUILL Audio Studio runs on the shared QuillVille Runtime. If it is not ' +
    'already installed, it will be downloaded now (about 230 MB, once) -- ' +
    'every QuillVille app reuses it afterward.',
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
        DownloadPage.Download;  // accessible progress page
      except
        if DownloadPage.AbortedByUser then
          MsgBox('The runtime download was cancelled. QUILL Audio Studio will ' +
                 'offer to download it again the first time you launch it.', mbInformation, MB_OK)
        else
          MsgBox('The QuillVille Runtime could not be downloaded: ' + GetExceptionMessage + #13#10#13#10 +
                 'You can install it later; QUILL Audio Studio will ' +
                 'offer to download it on first launch.', mbError, MB_OK);
        DownloadPage.Hide;
        Exit;
      end;
      RuntimeSetup := ExpandConstant('{tmp}\QuillVille-Runtime-Setup.exe');
      // Run the runtime installer. It installs the shared runtime (idempotent,
      // reference-counted) and shows its own accessible install progress.
      Exec(RuntimeSetup, '', '', SW_SHOWNORMAL, ewWaitUntilTerminated, ResultCode);
    finally
      DownloadPage.Hide;
    end;
  end;
end;
