; Quill Radio installer -- shared-runtime layout.
;
; Promoted from the validation-only quill-radio-shared.iss (2026-07-24):
; every shipping QuillVille product now installs the shared QuillVille
; Runtime once (at %LOCALAPPDATA%\QuillVille\Runtime\) and launches
; through it, instead of shipping a private Python inside its own
; onedir. The install-if-absent + reference-counting is owned by
; installer\shared-runtime.iss; this script's only job is to declare
; the three identifiers the fragment needs (RuntimeVersion,
; RuntimeSourceDir, AppRefId) and `#include` the fragment.
;
; The per-app payload is tiny: just the icon, the per-app C launcher
; (QuillRadio.exe, the portable-mode anchor; see
; storage_mode._has_portable_evidence), and (optionally) docs. The
; radio code itself lives in the shared runtime, launched via
; `{code:RuntimeExe} -m quill.apps.radio`.
;
; Build inputs (must exist before ISCC runs):
;   - the shared runtime at ..\..\runtime\dist\QuillVilleRuntime (built
;     by ..\..\runtime\quillville-runtime.spec, marker stamped,
;     ffmpeg/mpv staged into its tools\ so Radio finds them via
;     QUILL_APP_ROOT);
;   - the per-app QuillRadio.exe at ..\dist\QuillRadio-installer\QuillRadio.exe
;     (built by build_native_launcher.py);
;   - the per-app icon at ..\assets\quill-radio.ico;
;   - the rendered Radio docs at ..\dist\QuillRadio\docs.
;
; The standalone \scripts\build_release.ps1 chains those steps before
; the ISCC call; running ISCC directly requires all of them to exist
; already.

#define AppName "Quill Radio"
; Version is single-sourced from build_release.ps1, which passes
; /dAppVersion=<version> to ISCC. The literal below is only the fallback for a
; manual ISCC run and must be kept in step with build_release.ps1's $version.
#ifndef AppVersion
  #define AppVersion "3.2.0"
#endif
#define AppPublisher "Community Access"
#define AppURL "https://github.com/Community-Access/quill-radio"

; -- shared runtime parameters (read by installer\shared-runtime.iss) ----------
; AppRefId is the stable per-app key the fragment uses in
; runtime.state.json. It MUST stay "radio" forever -- renaming it
; would orphan the previous reference and double-count, leaving a
; phantom install that the uninstaller cannot reclaim.
#define RuntimeVersion "3.13.15"
#define RuntimeSourceDir "..\..\runtime\dist\QuillVilleRuntime"
#define AppRefId "radio"
; The media tools Radio declares (quill.apps.radio REQUIRED_COMPONENTS =
; ("ffmpeg", "mpv")). shared-runtime.iss installs these unconditionally, so
; Radio gets its playback engine whatever order the apps were installed in.
#define ToolFfmpeg
#define ToolMpv
; deno (yt-dlp's JavaScript runtime for YouTube) and the OptiLab Core adapter,
; both bundled and installed ungated so install order cannot drop them.
#define ToolDeno
#define ToolOptiLab

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
; Same AppId as the legacy onedir installer: it is the same product, so
; installing this variant upgrades an existing Radio in place rather than
; sitting beside it.
AppId={{35DAB52F-94BB-475C-BA97-A5059C85B3D1}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
VersionInfoVersion=3.2.0.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} accessible internet radio (shared runtime)
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
; The -Shared suffix stays: it is the name every QuillVille installer and
; the updater's asset matching share (QUILL Lite is QuillLite-Setup-Shared).
; Since 3.0.0 this is Radio's only installer -- the thin quill-radio-lite.iss
; was retired with the Companion zip, so a release publishes this and the
; portable zip and nothing else (scripts\build_release.ps1 says why).
OutputBaseFilename=Quill-Radio-Setup-Shared-{#AppVersion}
; A 64-bit Setup (Inno 7) so the LZMA dictionary can exceed the 32-bit cap.
; 128 MB reaches across ffmpeg.exe -> ffprobe.exe (97 MB of near-identical
; bytes the 32 MB ultra dictionary could never dedupe): 208.7 -> 181.8 MB
; measured on the 3.0.0 payload (2026-08-17). Costs the end user a 128 MB
; decompression buffer during install; the x64compatible line above already
; restricts installs to machines that have it.
SetupArchitecture=x64
Compression=lzma2/ultra
LZMADictionarySize=131072
SolidCompression=yes
WizardStyle=modern
CloseApplications=force
RestartApplications=no
UninstallDisplayName={#AppName} {#AppVersion}
UninstallDisplayIcon={app}\quill-radio.ico
SetupIconFile=..\assets\quill-radio.ico
LicenseFile=..\LICENSE
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Types]
Name: "full"; Description: "Full installation (recommended)"
Name: "compact"; Description: "Compact installation (program only, no bundled documentation)"
Name: "custom"; Description: "Custom installation"; Flags: iscustom

[Components]
; The runtime component is Flags: fixed -- it is part of every install
; type. Without it the per-app C launcher has no Python to spawn, and
; the app cannot launch. Disabling the "runtime" component is only
; useful on a Modify run when the user has uninstalled every other
; QuillVille app and wants the shared runtime removed (the fragment's
; CurUninstallStepChanged handles the unregister then).
Name: "runtime"; Description: "Shared QuillVille runtime (Python) -- installed once, reused by every QuillVille app"; Types: full compact custom; Flags: fixed
Name: "main"; Description: "{#AppName} (required)"; Types: full compact custom; Flags: fixed
Name: "docs"; Description: "Documentation (User Guide, Release Notes, Product Requirements)"; Types: full custom

[INI]
; The version THIS installer installed, read by quill.core.app_version for
; Check for Updates and About. The shared runtime carries every app's code, so
; the code's own constant says which runtime is here, not which app installer
; ran -- on 2026-09-29 a Radio runtime made QUILL Lite 1.0.0 call itself 1.1.0.
Filename: "{app}\quill-app-version.ini"; Section: "app"; Key: "version"; String: "{#AppVersion}"

[Files]
; Radio's own payload is tiny: just its icon, the per-app C launcher
; (the portable-mode anchor), and (optionally) its docs. The program
; itself lives in the shared runtime, installed by the fragment below.
Source: "..\assets\quill-radio.ico"; DestDir: "{app}"; Components: main; Flags: ignoreversion
; The installer's own launcher: built with the shared-runtime self-heal URL.
; The portable's QuillRadio.exe in ..\dist\QuillRadio has none (build_portable.py
; offline_portable_launcher: nothing downloads from a portable copy).
Source: "..\dist\QuillRadio-installer\QuillRadio.exe"; DestDir: "{app}"; Components: main; Flags: ignoreversion
; Which edition this is, so Check for Updates offers THIS installer back
; rather than guessing from a file extension (a user got the thin setup
; after installing the full one; see core/install_edition.py).
Source: "..\installer\edition-installer-full.txt"; DestDir: "{app}"; DestName: "quill-edition.txt"; Components: main; Flags: ignoreversion
Source: "..\dist\QuillRadio\docs\*"; DestDir: "{app}\docs"; Components: docs; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "*.epub"

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
; Every shortcut launches through {app}\QuillRadio.exe -- the native
; launcher, which resolves the shared runtime itself and runs
; `-m quill.apps.radio` in it (quilllite.iss says why a shortcut straight
; into the runtime exe is wrong).
; The guide shortcut opens the rendered HTML, as QUILL Lite's does: the .md
; source opens in whatever Windows associates with .md -- on most machines
; nothing at all, or a code editor that reads the markup aloud.
; AppUserModelID (3.0.2): the running app claims the same id
; (quill.core.runtime_apps, shortcuts_carry_id), so pinning Quill Radio to the
; taskbar pins THIS shortcut -- through QuillRadio.exe -- instead of the shared
; runtime with no arguments, which is what Windows pinned before and what
; started "not an app" in place of the radio (2026-09-27).
Name: "{group}\{#AppName}"; Filename: "{app}\QuillRadio.exe"; IconFilename: "{app}\quill-radio.ico"; AppUserModelID: "CommunityAccess.QuillRadio"; Components: main
Name: "{group}\{#AppName} User Guide"; Filename: "{app}\docs\userguide.html"; Components: docs
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\QuillRadio.exe"; IconFilename: "{app}\quill-radio.ico"; AppUserModelID: "CommunityAccess.QuillRadio"; Check: WantsDesktopIcon; Components: main

[UninstallDelete]
; Remove only Radio's own {app} payload. The shared runtime is left to
; the fragment's CurUninstallStepChanged, which deletes it only when
; unreferenced (no other QuillVille app still references the version
; that was registered at install time). The {app}\_internal tree that
; the old onedir layout used is gone in the shared layout -- the
; fragment owns the runtime files, not {app} -- so no upgrade hygiene
; is needed here.
Type: filesandordirs; Name: "{app}"

; Radio shares its settings/favorites/recordings store (%APPDATA%\Quill)
; with QUILL and the other apps; uninstall never touches that data.
; The full QUILL uninstaller owns that decision (it is the only
; uninstaller that knows the user's preferences).

[Code]
var
  { Native checkboxes; see the note at the top of [Icons]. }
  DesktopIconCheck: TNewCheckBox;
  LaunchCheck: TNewCheckBox;

{ A desktop icon an earlier Quill Radio left behind (3.0.1, 2026-09-27).
  Installers before 3.0 pointed it straight at the shared runtime,
  "QuillVilleRuntime.exe -m quill.apps.radio", which skips the native
  launcher -- so the app never learns where the runtime folder is and falls
  back to Windows Media instead of the bundled mpv engine. Such an icon is
  replaced, not kept: the box starts checked when one exists, the old one is
  removed, and [Icons] writes a fresh one through QuillRadio.exe. }
function HadDesktopIcon(): Boolean;
begin
  Result := FileExists(ExpandConstant('{commondesktop}\{#AppName}.lnk')) or
            FileExists(ExpandConstant('{userdesktop}\{#AppName}.lnk'));
end;

procedure RemoveOldDesktopIcons();
begin
  { Best effort: a per-user install may not be allowed to touch the public
    desktop, and a missing file is not an error. }
  DeleteFile(ExpandConstant('{commondesktop}\{#AppName}.lnk'));
  DeleteFile(ExpandConstant('{userdesktop}\{#AppName}.lnk'));
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
    RemoveOldDesktopIcons();
end;

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
  { Unchecked by default, as the task was -- unless an icon is already there,
    which is then kept (and repaired; see HadDesktopIcon). }
  DesktopIconCheck.Checked := HadDesktopIcon();
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
    ExecAsOriginalUser(ExpandConstant('{app}\QuillRadio.exe'), '', ExpandConstant('{app}'),
      SW_SHOWNORMAL, ewNoWait, LaunchResult);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  LaunchIfChosen(CurPageID);
end;
