; QUILL Transcribe installer -- shared-runtime layout.
;
; Follows standalone\weather\installer\quill-weather.iss (per-app C launcher +
; docs; the program itself lives in the shared QuillVille Runtime, launched via
; `{code:RuntimeExe} -m quill.apps.transcribe`) and adds what QUILL Lite's
; installer carries for dictation: the speech models and the sherpa-onnx package
; that runs them, beside the launcher rather than in the shared runtime.
;
; Build inputs (must exist before ISCC runs; build_release.ps1 makes them):
;   - the shared runtime at ..\..\runtime\dist\QuillVilleRuntime;
;   - the installer's own launcher at ..\dist\QuillTranscribe-installer\QuillTranscribe.exe
;     (built by build_portable.py, offline_portable_launcher);
;   - the per-app icon at ..\assets\quill-transcribe.ico;
;   - the rendered docs and dictation-models at ..\dist\QuillTranscribe\;
;   - the sherpa-onnx package at ..\..\..\build\dictation-python
;     (scripts\fetch_dictation_models.py).

#define AppName "QUILL Transcribe"
; Version is single-sourced from build_release.ps1, which passes
; /dAppVersion=<version> to ISCC. The literal below is only the fallback for a
; manual ISCC run and must be kept in step with build_release.ps1's $version.
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
; The build of this version and the Windows file version (X.Y.Z.B)
; (docs/release/RELEASE.md, "Build numbers"). build_release.ps1 passes
; /dAppBuild= and /dAppFileVersion=; these literals are only the fallback.
#ifndef AppBuild
  #define AppBuild "2"
#endif
#ifndef AppFileVersion
  #define AppFileVersion "1.0.0.2"
#endif
#define AppPublisher "Community Access"
#define AppURL "https://github.com/Community-Access/quill"

; -- shared runtime parameters (read by installer\shared-runtime.iss) ----------
; AppRefId is the stable per-app key the fragment uses in runtime.state.json.
; It MUST stay "transcribe" forever -- renaming it would orphan the reference.
#define RuntimeVersion "3.14.8"
#define RuntimeSourceDir "..\..\runtime\dist\QuillVilleRuntime"
#define AppRefId "transcribe"

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
; QUILL Transcribe's own AppId: a new product, never an upgrade of another.
AppId={{41BFB2AF-516C-4B79-BE05-0424D4A8C06D}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
VersionInfoVersion={#AppFileVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} dictation into any program (shared runtime)
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableDirPage=no
DisableProgramGroupPage=auto
AllowNoIcons=yes
; Current user only: no elevation, nothing machine-wide.
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
; The -Shared suffix is the name every QuillVille installer and the updater's
; asset matching share (Quill-Radio-Setup-Shared, QuillLite-Setup-Shared).
OutputBaseFilename=QUILL-Transcribe-Setup-Shared-{#AppVersion}
SetupArchitecture=x64
Compression=lzma2/ultra
LZMADictionarySize=131072
SolidCompression=yes
WizardStyle=modern
CloseApplications=force
RestartApplications=no
UninstallDisplayName={#AppName} {#AppVersion}
UninstallDisplayIcon={app}\quill-transcribe.ico
SetupIconFile=..\assets\quill-transcribe.ico
LicenseFile=..\LICENSE
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Types]
Name: "full"; Description: "Full installation (recommended)"
Name: "compact"; Description: "Compact installation (program only, no bundled documentation)"
Name: "custom"; Description: "Custom installation"; Flags: iscustom

[Components]
; The runtime component is Flags: fixed -- it is part of every install type.
; Without it the per-app C launcher has no Python to spawn.
Name: "runtime"; Description: "Shared QuillVille runtime (Python) -- installed once, reused by every QuillVille app"; Types: full compact custom; Flags: fixed
Name: "main"; Description: "{#AppName} (required), with its speech models"; Types: full compact custom; Flags: fixed
Name: "docs"; Description: "Documentation (User Guide, Release Notes, Product Requirements)"; Types: full custom

[INI]
; The app's installed version, independent of whichever shared runtime is present.
Filename: "{app}\quill-app-version.ini"; Section: "app"; Key: "version"; String: "{#AppVersion}"
Filename: "{app}\quill-app-version.ini"; Section: "app"; Key: "version_build"; String: "{#AppVersion}+{#AppBuild}"

[Files]
Source: "..\assets\quill-transcribe.ico"; DestDir: "{app}"; Components: main; Flags: ignoreversion
; The installer's own launcher: built with the shared-runtime self-heal URL.
; The portable's QuillTranscribe.exe in ..\dist\QuillTranscribe has none
; (build_portable.py offline_portable_launcher: nothing downloads from a portable copy).
Source: "..\dist\QuillTranscribe-installer\QuillTranscribe.exe"; DestDir: "{app}"; Components: main; Flags: ignoreversion
; The updater reads this to offer the right edition back (core/install_edition.py).
Source: "..\installer\edition-installer-full.txt"; DestDir: "{app}"; DestName: "quill-edition.txt"; Components: main; Flags: ignoreversion
Source: "..\dist\QuillTranscribe\docs\*"; DestDir: "{app}\docs"; Components: docs; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "*.epub"
; Dictation's speech models (Moonshine, Whisper, the pause detector), beside the
; launcher rather than in the shared runtime every QuillVille app installs. The
; launcher exports QUILL_LAUNCHER_DIR so quill.core.windows_dictation.engines
; finds them here. Nothing is downloaded at install or at first use.
Source: "..\dist\QuillTranscribe\dictation-models\*"; DestDir: "{app}\dictation-models"; Components: main; Flags: ignoreversion recursesubdirs createallsubdirs
; The sherpa-onnx package that runs them. The shared runtime deliberately does
; not freeze it in, so an installed copy imports it from here --
; quill.core.windows_dictation.engines.package_dirs.
Source: "..\..\..\build\dictation-python\*"; DestDir: "{app}\dictation-models\python"; Components: main; Flags: ignoreversion recursesubdirs createallsubdirs

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
Name: "{group}\{#AppName}"; Filename: "{app}\QuillTranscribe.exe"; IconFilename: "{app}\quill-transcribe.ico"; Components: main
Name: "{group}\{#AppName} User Guide"; Filename: "{app}\docs\userguide.html"; Components: docs
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\QuillTranscribe.exe"; IconFilename: "{app}\quill-transcribe.ico"; Check: WantsDesktopIcon; Components: main

[UninstallDelete]
; Remove only QUILL Transcribe's own {app} payload, models included. The shared
; runtime is left to the fragment's CurUninstallStepChanged, which deletes it
; only when unreferenced.
Type: filesandordirs; Name: "{app}"

; QUILL Transcribe shares the family data folder (%APPDATA%\Quill): its settings,
; the dictation word list, downloaded speech models and saved keys belong to the
; person and to the other apps too, so uninstall never touches them.

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
    controls. Unchecked by default. }
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
    out by then. Unchecked by default. Never offered in a silent install, nor
    when the page is asking to restart. }
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

{ The Finish button arrives in NextButtonClick as wpFinished. ewNoWait, and as
  the original (non-elevated) user, which is what Setup does for a postinstall
  entry. }
procedure LaunchIfChosen(CurPageID: Integer);
var
  LaunchResult: Integer;
begin
  if (CurPageID = wpFinished) and (LaunchCheck <> nil) and LaunchCheck.Checked
     and not WizardSilent then
    ExecAsOriginalUser(ExpandConstant('{app}\QuillTranscribe.exe'), '', ExpandConstant('{app}'),
      SW_SHOWNORMAL, ewNoWait, LaunchResult);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  LaunchIfChosen(CurPageID);
end;
