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
; Requires Inno Setup 7 (CreateDownloadPage needs 6.1+; the family builds with 7).

#define AppName "QUILL Audio Studio"
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
#define AppURL "https://github.com/Community-Access/quill-audio-studio"
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
; Same AppId as the full/shared installer: this is the same product.
AppId={{64D6B5F9-01E3-47D5-B49F-794DFC0106BF}}
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
; There is no [Tasks] section and no postinstall [Run] entry, on purpose.
; Both put their checkboxes in the wizard's TNewCheckListBox, a custom-drawn
; control that does not expose its checked state: a screen reader announces
; every box as "not checked" whatever it is. The [Code] section at the end of
; this script builds the same choices, with the same defaults, out of native
; Windows checkboxes (TNewCheckBox), which announce checked and not checked.
; tests/unit/scripts/test_installer_accessible_checkboxes.py keeps it so.
; Launch through the native launcher, which resolves the shared runtime.
Name: "{group}\{#AppName}"; Filename: "{app}\QuillAudioStudio.exe"; IconFilename: "{app}\quill-audio-studio.ico"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\QuillAudioStudio.exe"; IconFilename: "{app}\quill-audio-studio.ico"; Check: WantsDesktopIcon

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
var
  DownloadPage: TDownloadWizardPage;
  { Native checkboxes; see the note at the top of [Icons]. }
  DesktopIconCheck: TNewCheckBox;
  LaunchCheck: TNewCheckBox;

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
var
  TasksPage: TWizardPage;
begin
  DownloadPage := CreateDownloadPage(
    'Preparing the QuillVille Runtime',
    'QUILL Audio Studio runs on the shared QuillVille Runtime. If it is not ' +
    'already installed, it will be downloaded now (about 230 MB, once) -- ' +
    'every QuillVille app reuses it afterward.',
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
    ExecAsOriginalUser(ExpandConstant('{app}\QuillAudioStudio.exe'), '', ExpandConstant('{app}'),
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
