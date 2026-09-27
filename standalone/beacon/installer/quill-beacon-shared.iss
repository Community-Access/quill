; Quill Beacon installer -- shared-runtime layout.
;
; Promoted from the onedir layout to the shared QuillVille Runtime
; (2026-08-18). See standalone\radio\installer\quill-radio.iss for the full
; rationale. Beacon's application code already lives in the shared quill
; package (quill.apps.beacon), so the per-app payload is just the launcher,
; the icon, and docs, launched via `{code:RuntimeExe} -m quill.apps.beacon`.
; Beacon declares no media components; its build strips any staged
; ffmpeg/mpv from the runtime payload before this compiles.
;
; Build inputs (must exist before ISCC runs):
;   - the shared runtime at ..\..\runtime\dist\QuillVilleRuntime;
;   - the per-app QuillBeacon.exe at ..\dist\QuillBeacon-shared\QuillBeacon.exe
;     (built by scripts\build_native_launcher.py --product beacon);
;   - the rendered Beacon docs at ..\dist\QuillBeacon-shared\docs.

#define AppName "Quill Beacon"
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif
#define AppPublisher "Community Access"
#define AppURL "https://github.com/Community-Access/quill"

; -- shared runtime parameters (read by installer\shared-runtime.iss) ----------
; AppRefId MUST stay "beacon" forever; renaming orphans the reference.
#define RuntimeVersion "3.13.15"
#define RuntimeSourceDir "..\..\runtime\dist\QuillVilleRuntime"
#define AppRefId "beacon"

[Setup]
#ifdef Sign
SignTool=quilltrusted
SignedUninstaller=yes
#endif
; Same AppId as the legacy onedir installer: same product, so this variant
; upgrades an existing self-contained Beacon in place.
AppId={{6B1F0E92-3A7D-4C15-9E28-BEAC0FADE001}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} encrypted sync beacon (shared runtime)
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
OutputBaseFilename=Quill-Beacon-Setup-Shared-{#AppVersion}
SetupArchitecture=x64
Compression=lzma2/ultra
LZMADictionarySize=131072
SolidCompression=yes
WizardStyle=modern
CloseApplications=force
RestartApplications=no
UninstallDisplayName={#AppName} {#AppVersion}
UninstallDisplayIcon={app}\quill-beacon.ico
SetupIconFile=..\assets\quill-beacon.ico
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
Source: "..\assets\quill-beacon.ico"; DestDir: "{app}"; Components: main; Flags: ignoreversion
Source: "..\dist\QuillBeacon-shared\QuillBeacon.exe"; DestDir: "{app}"; Components: main; Flags: ignoreversion
Source: "..\installer\edition-installer-full.txt"; DestDir: "{app}"; DestName: "quill-edition.txt"; Components: main; Flags: ignoreversion
Source: "..\dist\QuillBeacon-shared\docs\*"; DestDir: "{app}\docs"; Components: docs; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

#include "..\..\..\installer\shared-runtime.iss"

[Icons]
; There is no [Tasks] section and no postinstall [Run] entry, on purpose.
; Both put their checkboxes in the wizard's TNewCheckListBox, a custom-drawn
; control that does not expose its checked state: a screen reader announces
; every box as "not checked" whatever it is. The [Code] section at the end of
; this script builds the same choices, with the same defaults, out of native
; Windows checkboxes (TNewCheckBox), which announce checked and not checked.
; tests/unit/scripts/test_installer_accessible_checkboxes.py keeps it so.
Name: "{group}\{#AppName}"; Filename: "{app}\QuillBeacon.exe"; IconFilename: "{app}\quill-beacon.ico"; Components: main
Name: "{group}\{#AppName} User Guide"; Filename: "{app}\docs\USER-GUIDE-QuillSync.md"; Components: docs
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\QuillBeacon.exe"; IconFilename: "{app}\quill-beacon.ico"; Check: WantsDesktopIcon; Components: main

[UninstallDelete]
; Only Beacon's own payload; the shared runtime is refcounted by the
; fragment, and the encrypted sync store is never touched by uninstall.
Type: filesandordirs; Name: "{app}"

[Code]
var
  { Native checkboxes; see the note at the top of [Icons]. }
  DesktopIconCheck: TNewCheckBox;
  LaunchCheck: TNewCheckBox;

procedure InitializeWizard;
var
  TasksPage: TWizardPage;
begin
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
    ExecAsOriginalUser(ExpandConstant('{app}\QuillBeacon.exe'), '', ExpandConstant('{app}'),
      SW_SHOWNORMAL, ewNoWait, LaunchResult);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  LaunchIfChosen(CurPageID);
end;
