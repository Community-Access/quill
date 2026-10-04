; Quill Weather -- THIN ("-Lite") installer.
;
; Ships ONLY the tiny native launcher + docs. It does NOT bundle the ~230 MB
; shared QuillVille Runtime; if the runtime is not already installed it
; downloads and runs the standalone QuillVille Runtime installer (a GitHub
; release asset), showing Inno Setup's built-in ACCESSIBLE download progress
; page. Every QuillVille app reuses that one runtime. Same AppId as the
; full/shared installer, so either one upgrades the other. Requires Inno 6.1+.

#define AppName "Quill Weather"
#ifndef AppVersion
  #define AppVersion "2.2.0"
#endif
; The build of this version and the Windows file version (X.Y.Z.B)
; (docs/release/RELEASE.md, "Build numbers"). build_release.ps1 passes
; /dAppBuild= and /dAppFileVersion=; these literals are only the fallback.
#ifndef AppBuild
  #define AppBuild "1"
#endif
#ifndef AppFileVersion
  #define AppFileVersion "2.2.0.1"
#endif
#define AppPublisher "Community Access"
#define AppURL "https://github.com/Community-Access/quill-weather"
#define RuntimeUrl "https://github.com/Community-Access/quill/releases/download/runtime-latest/QuillVille-Runtime-Setup.exe"

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
AppId={{7B0C2E14-9A3D-4F6B-B1E2-8C5D3A9F0E21}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
VersionInfoVersion={#AppFileVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} (thin installer -- shared runtime downloaded on demand)
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=auto
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputBaseFilename=Quill-Weather-Lite-Setup-{#AppVersion}
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
CloseApplications=force
UninstallDisplayName={#AppName} {#AppVersion} (Lite)
UninstallDisplayIcon={app}\quill-weather.ico
SetupIconFile=..\assets\quill-weather.ico
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\assets\quill-weather.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\QuillWeather\QuillWeather.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\QuillWeather\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

[Icons]
; There is no [Tasks] section and no postinstall [Run] entry, on purpose.
; Both put their checkboxes in the wizard's TNewCheckListBox, a custom-drawn
; control that does not expose its checked state: a screen reader announces
; every box as "not checked" whatever it is. The [Code] section at the end of
; this script builds the same choices, with the same defaults, out of native
; Windows checkboxes (TNewCheckBox), which announce checked and not checked.
; tests/unit/scripts/test_installer_accessible_checkboxes.py keeps it so.
Name: "{group}\{#AppName}"; Filename: "{app}\QuillWeather.exe"; IconFilename: "{app}\quill-weather.ico"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\QuillWeather.exe"; IconFilename: "{app}\quill-weather.ico"; Check: WantsDesktopIcon

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
var
  DownloadPage: TDownloadWizardPage;
  { Native checkboxes; see the note at the top of [Icons]. }
  DesktopIconCheck: TNewCheckBox;
  LaunchCheck: TNewCheckBox;

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
var
  TasksPage: TWizardPage;
begin
  DownloadPage := CreateDownloadPage(
    'Preparing the QuillVille Runtime',
    'Quill Weather runs on the shared QuillVille Runtime. If it is not already ' +
    'installed, it will be downloaded now (about 230 MB, once) -- every ' +
    'QuillVille app reuses it afterward.',
    @OnDownloadProgress);

  { The page the [Tasks] section used to produce, in the same place in the
    wizard (after the Start Menu folder page), rebuilt from announcing
    controls. Unchecked by default, as the tasks were. }
  TasksPage := CreateCustomPage(wpSelectProgramGroup,
    SetupMessage(msgWizardSelectTasks), SetupMessage(msgSelectTasksDesc));
  DesktopIconCheck := TNewCheckBox.Create(TasksPage);
  DesktopIconCheck.Parent := TasksPage.Surface;
  DesktopIconCheck.Left := 0;
  DesktopIconCheck.Top := ScaleY(8);
  DesktopIconCheck.Width := TasksPage.SurfaceWidth;
  DesktopIconCheck.Caption := 'Create a &desktop icon';
  DesktopIconCheck.Checked := False;
end;

function WantsDesktopIcon(): Boolean;
begin
  Result := (DesktopIconCheck <> nil) and DesktopIconCheck.Checked;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  { Built when the Finished page is reached, because its label is only laid
    out by then. Unchecked by default, matching the run entry this replaces.
    Never offered in a silent install (the entry was skipifsilent), nor when
    the page is asking to restart (Setup hides its run list then too). }
  if (CurPageID = wpFinished) and (LaunchCheck = nil) and not WizardSilent
     and not WizardForm.YesRadio.Visible then
  begin
    LaunchCheck := TNewCheckBox.Create(WizardForm);
    LaunchCheck.Parent := WizardForm.FinishedPage;
    LaunchCheck.Left := WizardForm.FinishedLabel.Left;
    LaunchCheck.Top := WizardForm.FinishedLabel.Top +
      WizardForm.FinishedLabel.Height + ScaleY(16);
    LaunchCheck.Width := WizardForm.FinishedLabel.Width;
    LaunchCheck.Caption := '&Launch {#AppName}';
    LaunchCheck.Checked := False;
  end;
end;

{ The Finish button arrives in NextButtonClick as wpFinished. ewNoWait, like
  the nowait run entry it replaces, and as the original (non-elevated) user,
  which is what Setup does for a postinstall entry. }
procedure LaunchIfChosen(CurPageID: Integer);
var
  LaunchResult: Integer;
begin
  if (CurPageID = wpFinished) and (LaunchCheck <> nil) and LaunchCheck.Checked
     and not WizardSilent then
    ExecAsOriginalUser(ExpandConstant('{app}\QuillWeather.exe'), '', ExpandConstant('{app}'),
      SW_SHOWNORMAL, ewNoWait, LaunchResult);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ResultCode: Integer;
  RuntimeSetup: String;
begin
  Result := True;
  LaunchIfChosen(CurPageID);
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
          MsgBox('The runtime download was cancelled. Quill Weather will ' +
                 'offer to download it again the first time you launch it.', mbInformation, MB_OK)
        else
          MsgBox('The QuillVille Runtime could not be downloaded: ' + GetExceptionMessage + #13#10#13#10 +
                 'You can install it later; Quill Weather will ' +
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
