; QUILL Cast installer -- shared-runtime layout.
;
; Promoted from the onedir layout to the shared QuillVille Runtime
; (2026-08-18). See standalone\radio\installer\quill-radio.iss for the full
; rationale; Cast follows the same pattern (per-app C launcher + docs only;
; the program itself lives in the shared runtime, launched via
; `{code:RuntimeExe} -m quill.apps.podcasts`). Cast declares ffmpeg, so the
; runtime payload this compiles must have tools\ffmpeg staged (its
; build_release.ps1 does that via Stage-QuillMediaTools) -- and must NOT
; have tools\mpv, which Cast never calls (the build strips it).
;
; Build inputs (must exist before ISCC runs):
;   - the shared runtime at ..\..\runtime\dist\QuillVilleRuntime with
;     tools\ffmpeg staged;
;   - the per-app QuillCast.exe at ..\dist\QuillCast-shared\QuillCast.exe
;     (built by scripts\build_native_launcher.py --product cast);
;   - the rendered Cast docs at ..\dist\QuillCast-shared\docs.

#define AppName "QUILL Cast"
#ifndef AppVersion
  #define AppVersion "2.0.0"
#endif
; The build of this version and the Windows file version (X.Y.Z.B)
; (docs/release/RELEASE.md, "Build numbers"). build_release.ps1 passes
; /dAppBuild= and /dAppFileVersion=; these literals are only the fallback.
#ifndef AppBuild
  #define AppBuild "1"
#endif
#ifndef AppFileVersion
  #define AppFileVersion "2.0.0.1"
#endif
#define AppPublisher "Community Access"
#define AppURL "https://github.com/Community-Access/quill-cast"

; -- shared runtime parameters (read by installer\shared-runtime.iss) ----------
; AppRefId MUST stay "cast" forever (quill.apps.podcasts registers "cast");
; renaming it would orphan the previous reference in runtime.state.json.
#define RuntimeVersion "3.13.15"
#define RuntimeSourceDir "..\..\runtime\dist\QuillVilleRuntime"
#define AppRefId "cast"
; The launcher both shared-runtime editions install into {app}. It is
; ALSO the quill-cast:// URI handler below, which is what needs it named:
; a protocol handler is one exe plus "%1", so it cannot be expressed as the
; runtime plus "-m quill.apps.podcasts" the way the shortcuts are.
; Spelled differently from quill-cast.iss's QUILLCast.exe on purpose --
; that is the self-contained onedir's PyInstaller output, a different file.
#define AppExeName "QuillCast.exe"
; quill.apps.podcasts REQUIRED_COMPONENTS = ("ffmpeg",). No mpv: Cast plays
; through wx.media, and the 110 MB it never calls stays out of its installer.
#define ToolFfmpeg

[Setup]
#ifdef Sign
SignTool=quilltrusted
SignedUninstaller=yes
#endif
; Same AppId as the legacy onedir installer: same product, so this variant
; upgrades an existing self-contained Cast in place rather than sitting
; beside it.
AppId={{316B5D30-E16B-4973-95B6-968F5D897FD7}}
AppName={#AppName}
AppVersion={#AppVersion}
VersionInfoVersion={#AppFileVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} accessible podcast player (shared runtime)
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
OutputBaseFilename=QUILL-Cast-Setup-Shared-{#AppVersion}
; 64-bit Setup (Inno 7) + 128 MB LZMA dictionary: dedupes the runtime's
; near-identical ffmpeg/ffprobe pair in the solid stream (-27 MB on Radio).
SetupArchitecture=x64
Compression=lzma2/ultra
LZMADictionarySize=131072
SolidCompression=yes
WizardStyle=modern
CloseApplications=force
RestartApplications=no
UninstallDisplayName={#AppName} {#AppVersion}
UninstallDisplayIcon={app}\quill-cast.ico
SetupIconFile=..\assets\quill-cast.ico
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

[INI]
; The version THIS installer installed, read by quill.core.app_version for
; Check for Updates and About. The shared runtime carries every app's code, so
; the code's own constant says which runtime is here, not which app installer
; ran (the same marker Quill Radio and QUILL Lite write; release-channels plan,
; Phase 0).
Filename: "{app}\quill-app-version.ini"; Section: "app"; Key: "version"; String: "{#AppVersion}"
; The build, beside the version it belongs to (quill.core.app_version says
; why it repeats the version rather than holding the bare number).
Filename: "{app}\quill-app-version.ini"; Section: "app"; Key: "version_build"; String: "{#AppVersion}+{#AppBuild}"

[Files]
Source: "..\assets\quill-cast.ico"; DestDir: "{app}"; Components: main; Flags: ignoreversion
Source: "..\dist\QuillCast-shared\QuillCast.exe"; DestDir: "{app}"; Components: main; Flags: ignoreversion
; Which edition this is, so Check for Updates offers THIS installer back
; (see core/install_edition.py).
Source: "..\installer\edition-installer-full.txt"; DestDir: "{app}"; DestName: "quill-edition.txt"; Components: main; Flags: ignoreversion
Source: "..\dist\QuillCast-shared\docs\*"; DestDir: "{app}\docs"; Components: docs; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; The shared runtime (install-if-absent) + reference registration + orphan
; removal on uninstall. Defines RuntimeDir/RuntimeExe used by [Icons]/[Run].
#include "..\..\..\installer\shared-runtime.iss"

[Icons]
; There is no [Tasks] section and no postinstall [Run] entry, on purpose.
; Both put their checkboxes in the wizard's TNewCheckListBox, a custom-drawn
; control that does not expose its checked state: a screen reader announces
; every box as "not checked" whatever it is. The [Code] section at the end of
; this script builds the same choices, with the same defaults, out of native
; Windows checkboxes (TNewCheckBox), which announce checked and not checked.
; tests/unit/scripts/test_installer_accessible_checkboxes.py keeps it so.
Name: "{group}\{#AppName}"; Filename: "{app}\QuillCast.exe"; IconFilename: "{app}\quill-cast.ico"; Components: main
Name: "{group}\{#AppName} User Guide"; Filename: "{app}\docs\userguide.md"; Components: docs
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\QuillCast.exe"; IconFilename: "{app}\quill-cast.ico"; Check: WantsDesktopIcon; Components: main

[UninstallDelete]
; Only Cast's own payload; the shared runtime is refcounted by the fragment.
; Subscriptions, downloads and notes live in %APPDATA%\Quill and are never
; touched by uninstall.
Type: filesandordirs; Name: "{app}"

[Registry]

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
    ExecAsOriginalUser(ExpandConstant('{app}\QuillCast.exe'), '', ExpandConstant('{app}'),
      SW_SHOWNORMAL, ewNoWait, LaunchResult);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  LaunchIfChosen(CurPageID);
end;
