; Quill Converter installer -- shared-runtime layout.
;
; Converter's first installer (2026-09-26). Until now it shipped only as the
; portable zip; this gives it the same two downloads Quill Radio 3.0.0 and
; QUILL Lite publish -- this installer and the portable zip, nothing else
; (scripts\build_release.ps1 says why there is no thin installer and no
; Companion zip).
;
; The same shape every QuillVille app has used since 2026-07-24: a per-app C
; launcher plus docs, with the program itself living in the shared QuillVille
; Runtime and launched through `{app}\QuillConverter.exe`, the native launcher.
; See standalone\radio\installer\quill-radio.iss for the full rationale. The
; install-if-absent + reference counting is owned by installer\shared-runtime.iss;
; this script declares the identifiers it needs and `#include`s it.
;
; The Explorer verb (1.0.0, decided 2026-09-26): a native checkbox, checked by
; default, adds "Convert with Quill Converter" to the right-click menu of every
; audio and video type the Converter reads, per user (HKCU), under the key
; QuillConverter.Convert -- distinct from QUILL's own Quill.convert, so the two
; never remove each other's -- and the uninstaller removes it. The block is
; generated from the format catalogue (explorer-verb.isi,
; scriptsuild_converter_verb_iss.py); a test keeps it current. Selecting many
; files queues them all in one window (the IPC hand-over in the app).
;
; Build inputs (must exist before ISCC runs):
;   - the shared runtime at ..\..\runtime\dist\QuillVilleRuntime (built by
;     ..\..\runtime\build_runtime.ps1, marker stamped, ffmpeg staged into its
;     tools\ by scripts\StageMediaTools.ps1 so Converter finds it via
;     QUILL_APP_ROOT);
;   - the per-app QuillConverter.exe at ..\dist\QuillConverter\QuillConverter.exe
;     (built by build_native_launcher.py, via build_portable.py);
;   - the per-app icon at ..\assets\quill-converter.ico;
;   - the rendered Converter docs at ..\dist\QuillConverter\docs.
;
; ..\scripts\build_release.ps1 chains those steps before the ISCC call; running
; ISCC directly requires all of them to exist already.

#define AppName "Quill Converter"
; Version is single-sourced from build_release.ps1, which passes
; /dAppVersion=<version> to ISCC. The literal below is only the fallback for a
; manual ISCC run and must be kept in step with build_release.ps1's $version
; (and with _VERSION in quill\apps\converter.py).
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppPublisher "Community Access"
#define AppURL "https://github.com/Community-Access/quill"

; -- shared runtime parameters (read by installer\shared-runtime.iss) ----------
; AppRefId is the stable per-app key the fragment uses in runtime.state.json.
; It MUST stay "converter" forever -- renaming it would orphan the previous
; reference and double-count, leaving a phantom install the uninstaller cannot
; reclaim. It matches quill.apps.converter's register_running_app("converter").
#define RuntimeVersion "3.13.15"
#define RuntimeSourceDir "..\..\runtime\dist\QuillVilleRuntime"
#define AppRefId "converter"
; The media tools Converter declares (quill.apps.converter REQUIRED_COMPONENTS =
; ("ffmpeg", "mpv")). Without ffmpeg the app can only write WAV; mpv is the
; Chapter Workbench's player, for exact seeking.
#define ToolFfmpeg
#define ToolMpv
; deno, yt-dlp's JavaScript runtime for YouTube, for Convert from URL (one
; video, a playlist or a channel). Without it YouTube links can fail.
#define ToolDeno

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
; Converter's own AppId, new with this installer. Never reuse it for another
; product, and never change it: it is how an update finds this install.
AppId={{9E16BE7C-500F-4932-9F24-9DB221552FD7}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
VersionInfoVersion=1.0.0.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} accessible audio and video converter (shared runtime)
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
; The -Shared suffix is the name every QuillVille installer and the updater's
; asset matching share (Quill-Radio-Setup-Shared, QuillLite-Setup-Shared).
OutputBaseFilename=Quill-Converter-Setup-Shared-{#AppVersion}
; Kept in step with quill-radio.iss (2026-08-17): 64-bit Setup (Inno 7) + a
; 128 MB LZMA dictionary, which reaches across ffmpeg.exe -> ffprobe.exe (near-
; identical bytes the 32 MB ultra dictionary could never dedupe).
SetupArchitecture=x64
Compression=lzma2/ultra
LZMADictionarySize=131072
SolidCompression=yes
WizardStyle=modern
CloseApplications=force
RestartApplications=no
UninstallDisplayName={#AppName} {#AppVersion}
UninstallDisplayIcon={app}\quill-converter.ico
SetupIconFile=..\assets\quill-converter.ico
; Converter carries no LICENSE of its own; it is the QUILL repository's (MIT).
LicenseFile=..\..\..\LICENSE
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Types]
Name: "full"; Description: "Full installation (recommended)"
Name: "compact"; Description: "Compact installation (program only, no bundled documentation)"
Name: "custom"; Description: "Custom installation"; Flags: iscustom

[Components]
; The runtime component is Flags: fixed -- it is part of every install type.
; Without it the per-app C launcher has no Python to spawn, and no ffmpeg.
Name: "runtime"; Description: "Shared QuillVille runtime (Python) -- installed once, reused by every QuillVille app"; Types: full compact custom; Flags: fixed
Name: "main"; Description: "{#AppName} (required)"; Types: full compact custom; Flags: fixed
Name: "docs"; Description: "Documentation (User Guide, Release Notes, Changelog, Product Requirements)"; Types: full custom

[Files]
; Converter's own payload is tiny: its icon, the per-app C launcher (the
; portable-mode anchor), and (optionally) its docs. The program itself lives in
; the shared runtime, installed by the fragment below.
Source: "..\assets\quill-converter.ico"; DestDir: "{app}"; Components: main; Flags: ignoreversion
Source: "..\dist\QuillConverter\QuillConverter.exe"; DestDir: "{app}"; Components: main; Flags: ignoreversion
; Which edition this is, so Check for Updates offers THIS installer back rather
; than guessing from a file extension (core/install_edition.py).
Source: "..\installer\edition-installer-full.txt"; DestDir: "{app}"; DestName: "quill-edition.txt"; Components: main; Flags: ignoreversion
Source: "..\dist\QuillConverter\docs\*"; DestDir: "{app}\docs"; Components: docs; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "*.epub"

; The Explorer verb's registry entries, gated by WantsExplorerVerb. Included
; before the shared-runtime fragment, which ends in a [Code] section.
#include "explorer-verb.isi"

; The shared runtime (install-if-absent) + reference registration + orphan
; removal on uninstall, plus the tools this app declares (ToolFfmpeg/ToolMpv).
#include "..\..\..\installer\shared-runtime.iss"

[Icons]
; There is no [Tasks] section and no postinstall [Run] entry, on purpose.
; Both put their checkboxes in the wizard's TNewCheckListBox, a custom-drawn
; control that does not expose its checked state: a screen reader announces
; every box as "not checked" whatever it is. The [Code] section at the end of
; this script builds the same choices out of native Windows checkboxes
; (TNewCheckBox), which announce checked and not checked. Both are unchecked by
; default. tests/unit/scripts/test_installer_accessible_checkboxes.py keeps it so.
; Every shortcut launches through {app}\QuillConverter.exe -- the native
; launcher, which resolves the shared runtime itself and runs
; `-m quill.apps.converter` in it (quilllite.iss says why a shortcut straight
; into the runtime exe is wrong). The guide shortcut opens the rendered HTML:
; the .md source opens in whatever Windows associates with .md, which on most
; machines is nothing at all.
Name: "{group}\{#AppName}"; Filename: "{app}\QuillConverter.exe"; IconFilename: "{app}\quill-converter.ico"; Components: main
Name: "{group}\{#AppName} User Guide"; Filename: "{app}\docs\userguide.html"; Components: docs
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\QuillConverter.exe"; IconFilename: "{app}\quill-converter.ico"; Check: WantsDesktopIcon; Components: main

[UninstallDelete]
; Remove only Converter's own {app} payload. The shared runtime is left to the
; fragment's CurUninstallStepChanged, which deletes it only when unreferenced.
Type: filesandordirs; Name: "{app}"

; Converter shares its settings store (%APPDATA%\Quill) with QUILL and the other
; apps; uninstall never touches that data, and never touches converted files.

[Code]
var
  { Native checkboxes; see the note at the top of [Icons]. }
  DesktopIconCheck: TNewCheckBox;
  ExplorerVerbCheck: TNewCheckBox;
  LaunchCheck: TNewCheckBox;

procedure InitializeWizard;
var
  TasksPage: TWizardPage;
begin
  { The page a [Tasks] section would produce, in the place the family puts it
    (after the Start Menu folder page, which follows Select Destination), built
    from announcing controls. Unchecked by default. }
  TasksPage := CreateCustomPage(wpSelectProgramGroup,
    SetupMessage(msgWizardSelectTasks), SetupMessage(msgSelectTasksDesc));
  DesktopIconCheck := TNewCheckBox.Create(TasksPage);
  DesktopIconCheck.Parent := TasksPage.Surface;
  DesktopIconCheck.Left := 0;
  DesktopIconCheck.Top := ScaleY(8);
  DesktopIconCheck.Width := TasksPage.SurfaceWidth;
  DesktopIconCheck.Caption := 'Create a &desktop icon';
  DesktopIconCheck.Checked := False;
  ExplorerVerbCheck := TNewCheckBox.Create(TasksPage);
  ExplorerVerbCheck.Parent := TasksPage.Surface;
  ExplorerVerbCheck.Left := 0;
  ExplorerVerbCheck.Top := DesktopIconCheck.Top + DesktopIconCheck.Height + ScaleY(12);
  ExplorerVerbCheck.Width := TasksPage.SurfaceWidth;
  ExplorerVerbCheck.Caption := 'Add "Convert with Quill Converter" to the File &Explorer right-click menu';
  ExplorerVerbCheck.Checked := True;
end;

function WantsExplorerVerb(): Boolean;
begin
  Result := (ExplorerVerbCheck = nil) or ExplorerVerbCheck.Checked;
end;

function WantsDesktopIcon(): Boolean;
begin
  Result := (DesktopIconCheck <> nil) and DesktopIconCheck.Checked;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  { Built when the Finished page is reached, because its label is only laid
    out by then. Unchecked by default. Never offered in a silent install, nor
    when the page is asking to restart (Setup hides its run list then too). }
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

{ The Finish button arrives in NextButtonClick as wpFinished. ewNoWait, so the
  installer closes rather than waiting on the app, and as the original
  (non-elevated) user, which is what Setup does for a postinstall entry. }
procedure LaunchIfChosen(CurPageID: Integer);
var
  LaunchResult: Integer;
begin
  if (CurPageID = wpFinished) and (LaunchCheck <> nil) and LaunchCheck.Checked
     and not WizardSilent then
    ExecAsOriginalUser(ExpandConstant('{app}\QuillConverter.exe'), '', ExpandConstant('{app}'),
      SW_SHOWNORMAL, ewNoWait, LaunchResult);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  LaunchIfChosen(CurPageID);
end;
