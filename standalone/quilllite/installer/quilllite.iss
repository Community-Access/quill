; QUILL Lite installer -- shared-runtime layout.
;
; Named quilllite.iss rather than quill-lite.iss on purpose: the family
; reserves the "*-lite.iss" suffix for the THIN installer flavour, and
; "quill-lite.iss" ends in it, so the shared installer was being audited as a
; thin one (tests/unit/structure/test_lite_installer_assets.py globs
; standalone/*/installer/*-lite.iss). The product key is "quilllite"
; everywhere else -- the folder, AppRefId, the launcher product -- so the
; installers match it.
;
; The same shape every QuillVille app has used since 2026-07-24: a per-app C
; launcher plus docs, with the program itself living in the shared QuillVille
; Runtime and launched through `{app}\QuillLite.exe`, the native launcher.
; See standalone\radio\installer\quill-radio.iss for the full rationale.
;
; QUILL Lite is the leanest app in the family after Weather -- one editor
; control, six small windows, no ffmpeg and no libmpv -- so the per-app payload
; is just the icon, the C launcher, and (optionally) the docs.
;
; Build inputs (must exist before ISCC runs):
;   - the shared runtime at ..\..\runtime\dist\QuillVilleRuntime
;     (built by ..\..\runtime\quillville-runtime.spec, marker stamped;
;     build_runtime.ps1 chains the spec, the marker stamp, and the staging);
;   - the per-app QuillLite.exe at ..\dist\QuillLite-installer\QuillLite.exe
;     (built by build_native_launcher.py);
;   - the per-app icon at ..\assets\quill-lite.ico;
;   - the rendered QUILL Lite docs at ..\dist\QuillLite\docs.

; The name people see and hear: window titles, the Start Menu, Add/Remove
; Programs, the Open With list. Changed from "QuillLite" on 2026-09-25. Every
; machine identifier -- the exe, the install folder, the data folder, AppId, the
; registry keys, the release assets -- keeps the old one-word spelling, so an
; upgrade finds everything where it left it.
#define AppName "QUILL Lite"
; Version is single-sourced from build_release.ps1, which passes
; /dAppVersion=<version> to ISCC. The literal below is only the fallback for a
; manual ISCC run and must be kept in step with build_release.ps1's $version.
#ifndef AppVersion
  #define AppVersion "1.2.0"
#endif
#define AppPublisher "Community Access"
#define AppURL "https://github.com/Community-Access/quill"

; -- shared runtime parameters (read by installer\shared-runtime.iss) ----------
; AppRefId is the stable per-app key the fragment uses in runtime.state.json.
; It MUST stay "quilllite" forever -- renaming it would orphan the previous
; reference and double-count, leaving a phantom install the uninstaller cannot
; reclaim.
#define RuntimeVersion "3.13.15"
#define RuntimeSourceDir "..\..\runtime\dist\QuillVilleRuntime"
#define AppRefId "quilllite"

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
AppId={{3F1B6C08-2D47-4A19-9E63-5C7A08B41D22}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
VersionInfoVersion=1.2.0.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} accessible plain text and rich text editor (shared runtime)
; The folder keeps the old name: an existing install upgrades in place.
DefaultDirName={autopf}\QuillLite
DefaultGroupName={#AppName}
; Not the previous group: that is the old "QuillLite" name, which [InstallDelete]
; removes so the Start Menu does not end up with both.
UsePreviousGroup=no
DisableDirPage=no
DisableProgramGroupPage=auto
AllowNoIcons=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputBaseFilename=QuillLite-Setup-Shared-{#AppVersion}
; Kept in step with quill-radio.iss (2026-08-17): 64-bit Setup (Inno 7) +
; 128 MB LZMA dictionary, which dedupes near-identical files in the embedded
; runtime's solid stream.
SetupArchitecture=x64
Compression=lzma2/ultra
LZMADictionarySize=131072
SolidCompression=yes
WizardStyle=modern
CloseApplications=force
RestartApplications=no
UninstallDisplayName={#AppName} {#AppVersion}
UninstallDisplayIcon={app}\quill-lite.ico
SetupIconFile=..\assets\quill-lite.ico
LicenseFile=..\LICENSE
SetupLogging=yes
; The [Registry] section registers QUILL Lite as a text editor; this tells
; Explorer to refresh Open With and Default apps when Setup finishes.
ChangesAssociations=yes

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
Name: "main"; Description: "{#AppName} (required)"; Types: full compact custom; Flags: fixed
Name: "docs"; Description: "Documentation (User Guide, Release Notes, Product Requirements)"; Types: full custom

[INI]
; The version THIS installer installed, read by quill.core.app_version for
; Check for Updates and About. The shared runtime carries every app's code, so
; the code's own constant says which runtime is here, not which app installer
; ran -- on 2026-09-29 a Radio runtime made QUILL Lite 1.0.0 call itself 1.1.0.
Filename: "{app}\quill-app-version.ini"; Section: "app"; Key: "version"; String: "{#AppVersion}"

[Files]
Source: "..\assets\quill-lite.ico"; DestDir: "{app}"; Components: main; Flags: ignoreversion
; The installer's own launcher: built with the shared-runtime self-heal URL.
; The portable's QuillLite.exe in ..\dist\QuillLite has none (build_portable.py
; offline_portable_launcher: nothing downloads from a portable copy).
Source: "..\dist\QuillLite-installer\QuillLite.exe"; DestDir: "{app}"; Components: main; Flags: ignoreversion
; The updater reads this to offer the right edition back (core/install_edition.py).
Source: "..\installer\edition-installer-full.txt"; DestDir: "{app}"; DestName: "quill-edition.txt"; Components: main; Flags: ignoreversion
Source: "..\dist\QuillLite\docs\*"; DestDir: "{app}\docs"; Components: docs; Flags: ignoreversion recursesubdirs createallsubdirs
; Dictation's speech models (Moonshine, Whisper, the pause detector), beside the
; launcher rather than in the shared runtime every QuillVille app installs. The
; launcher exports QUILL_LAUNCHER_DIR so quill.core.windows_dictation.engines
; finds them here. Nothing is downloaded at install or at first use.
Source: "..\dist\QuillLite\dictation-models\*"; DestDir: "{app}\dictation-models"; Components: main; Flags: ignoreversion recursesubdirs createallsubdirs
; The sherpa-onnx package that runs them. The shared runtime deliberately does
; not freeze it in (it would shadow QUILL's engine packs), so an installed copy
; imports it from here -- quill.core.windows_dictation.engines.package_dirs.
Source: "..\..\..\build\dictation-python\*"; DestDir: "{app}\dictation-models\python"; Components: main; Flags: ignoreversion recursesubdirs createallsubdirs

; The shared runtime (install-if-absent) + reference registration + orphan
; removal on uninstall. Defines RuntimeDir/RuntimeExe used by [Icons]/[Run].
#include "..\..\..\installer\shared-runtime.iss"

[InstallDelete]
; The shortcuts from before the display name became "QUILL Lite" (2026-09-25).
; Without these an upgrade leaves the old Start Menu folder and desktop icon
; behind, and the Start Menu reads out the product twice under two spellings.
Type: filesandordirs; Name: "{autoprograms}\QuillLite"
Type: files; Name: "{autodesktop}\QuillLite.lnk"

[Icons]
; There is no [Tasks] section and no postinstall [Run] entry, on purpose.
; Both put their checkboxes in the wizard's TNewCheckListBox, a custom-drawn
; control that does not expose its checked state: a screen reader announces
; every box as "not checked" whatever it is. The [Code] section at the end of
; this script builds the same choices, with the same defaults, out of native
; Windows checkboxes (TNewCheckBox), which announce checked and not checked.
; tests/unit/scripts/test_installer_accessible_checkboxes.py keeps it so.
; Every shortcut launches through {app}\QuillLite.exe -- the native launcher,
; which resolves the shared runtime itself and runs `-m quill.apps.lite` in it.
;
; It used to name {code:RuntimeExe} directly, which is wrong for a second
; reason: the launcher is the only thing that exports QUILL_APP_ROOT at all,
; and a shortcut into the runtime exe exports nothing.
;
; It does NOT, on its own, give the app its identity, and the note that used to
; stand here said it did. On a shared-runtime install the launcher finds no
; interpreter beside itself, so it resolves the shared runtime and exports
; QUILL_APP_ROOT=<the runtime folder> -- deliberately, because that is where
; the staged tools\ and vendor\ payloads live. quill.core.install_edition then
; reads THAT folder, finds no quill-edition.txt, no uninstaller and no data\,
; and concludes the user is running the Companion zip (verified 2026-09-15).
; Harmless for QUILL Lite from now on, because QUILL Lite publishes no Companion
; zip and the updater falls through to this installer -- the right answer by
; luck rather than by design. The two meanings of "app root" need separating
; before it is right on purpose.
Name: "{group}\{#AppName}"; Filename: "{app}\QuillLite.exe"; IconFilename: "{app}\quill-lite.ico"; Components: main
Name: "{group}\{#AppName} User Guide"; Filename: "{app}\docs\userguide.html"; Components: docs
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\QuillLite.exe"; IconFilename: "{app}\quill-lite.ico"; Check: WantsDesktopIcon; Components: main

[Registry]
; QUILL Lite tells Windows it is a text editor that CAN open these types, on
; every install, and takes nothing over. Windows keeps the choice of which app
; opens a type for the user alone (a UserChoice key only Windows can write, and
; nothing here touches it); these keys put QUILL Lite in Open With and in
; Settings > Apps > Default apps, where that choice is made. Tools > Make QUILL
; Lite My Text Editor writes the same keys for one account and opens that page.
;
; This replaced an optional "assoc" component on 2026-10-03. Components are a
; TNewCheckListBox, which a screen reader reads as unchecked whatever its state,
; and offering nothing that takes over left nothing worth asking about.
;
; HKA: HKCU for a per-user install, HKLM for an administrator one. The types are
; the ones QUILL Lite really opens; quill/core/lite/windows_editor.py EXTENSIONS
; holds the same list, and tests/unit/scripts/test_quilllite_text_editor_installer.py
; keeps the two equal.
Root: HKA; Subkey: "Software\Classes\QuillLite.Document"; ValueType: string; ValueName: ""; ValueData: "{#AppName} Document"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\QuillLite.Document"; ValueType: string; ValueName: "FriendlyTypeName"; ValueData: "{#AppName} Document"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\QuillLite.Document\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\quill-lite.ico"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\QuillLite.Document\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\QuillLite.exe"" ""%1"""; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Applications\QuillLite.exe"; ValueType: string; ValueName: "FriendlyAppName"; ValueData: "{#AppName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Applications\QuillLite.exe\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\quill-lite.ico"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Applications\QuillLite.exe\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\QuillLite.exe"" ""%1"""; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Applications\QuillLite.exe\SupportedTypes"; ValueType: string; ValueName: ".txt"; ValueData: ""; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Applications\QuillLite.exe\SupportedTypes"; ValueType: string; ValueName: ".text"; ValueData: ""; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Applications\QuillLite.exe\SupportedTypes"; ValueType: string; ValueName: ".log"; ValueData: ""; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Applications\QuillLite.exe\SupportedTypes"; ValueType: string; ValueName: ".md"; ValueData: ""; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Applications\QuillLite.exe\SupportedTypes"; ValueType: string; ValueName: ".markdown"; ValueData: ""; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Applications\QuillLite.exe\SupportedTypes"; ValueType: string; ValueName: ".rtf"; ValueData: ""; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Applications\QuillLite.exe\SupportedTypes"; ValueType: string; ValueName: ".html"; ValueData: ""; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Applications\QuillLite.exe\SupportedTypes"; ValueType: string; ValueName: ".htm"; ValueData: ""; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Applications\QuillLite.exe\SupportedTypes"; ValueType: string; ValueName: ".csv"; ValueData: ""; Flags: uninsdeletekey
; One value in each type's own list, removed on uninstall; the type's key is
; shared with every other app and is never deleted.
Root: HKA; Subkey: "Software\Classes\.txt\OpenWithProgids"; ValueType: string; ValueName: "QuillLite.Document"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.text\OpenWithProgids"; ValueType: string; ValueName: "QuillLite.Document"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.log\OpenWithProgids"; ValueType: string; ValueName: "QuillLite.Document"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.md\OpenWithProgids"; ValueType: string; ValueName: "QuillLite.Document"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.markdown\OpenWithProgids"; ValueType: string; ValueName: "QuillLite.Document"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.rtf\OpenWithProgids"; ValueType: string; ValueName: "QuillLite.Document"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.html\OpenWithProgids"; ValueType: string; ValueName: "QuillLite.Document"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.htm\OpenWithProgids"; ValueType: string; ValueName: "QuillLite.Document"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.csv\OpenWithProgids"; ValueType: string; ValueName: "QuillLite.Document"; ValueData: ""; Flags: uninsdeletevalue
; Capabilities + RegisteredApplications: what Default apps lists QUILL Lite by.
Root: HKA; Subkey: "Software\QuillLite"; Flags: uninsdeletekeyifempty
Root: HKA; Subkey: "Software\QuillLite\Capabilities"; ValueType: string; ValueName: "ApplicationName"; ValueData: "{#AppName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\QuillLite\Capabilities"; ValueType: string; ValueName: "ApplicationDescription"; ValueData: "An accessible text editor for plain text, Markdown, rich text and HTML, built for screen readers."; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\QuillLite\Capabilities"; ValueType: string; ValueName: "ApplicationIcon"; ValueData: "{app}\quill-lite.ico"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\QuillLite\Capabilities\FileAssociations"; ValueType: string; ValueName: ".txt"; ValueData: "QuillLite.Document"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\QuillLite\Capabilities\FileAssociations"; ValueType: string; ValueName: ".text"; ValueData: "QuillLite.Document"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\QuillLite\Capabilities\FileAssociations"; ValueType: string; ValueName: ".log"; ValueData: "QuillLite.Document"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\QuillLite\Capabilities\FileAssociations"; ValueType: string; ValueName: ".md"; ValueData: "QuillLite.Document"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\QuillLite\Capabilities\FileAssociations"; ValueType: string; ValueName: ".markdown"; ValueData: "QuillLite.Document"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\QuillLite\Capabilities\FileAssociations"; ValueType: string; ValueName: ".rtf"; ValueData: "QuillLite.Document"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\QuillLite\Capabilities\FileAssociations"; ValueType: string; ValueName: ".html"; ValueData: "QuillLite.Document"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\QuillLite\Capabilities\FileAssociations"; ValueType: string; ValueName: ".htm"; ValueData: "QuillLite.Document"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\QuillLite\Capabilities\FileAssociations"; ValueType: string; ValueName: ".csv"; ValueData: "QuillLite.Document"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\RegisteredApplications"; ValueType: string; ValueName: "{#AppName}"; ValueData: "Software\QuillLite\Capabilities"; Flags: uninsdeletevalue

[UninstallDelete]
; Remove only QUILL Lite's own {app} payload. The shared runtime is left to the
; fragment's CurUninstallStepChanged, which deletes it only when unreferenced.
Type: filesandordirs; Name: "{app}"

; %LOCALAPPDATA%\QuillLite -- settings, recent files, and any recovered work --
; is deliberately NOT removed. Recovery slots are the one thing in that folder
; somebody may not have finished with, and an uninstaller is the worst possible
; moment to discover that. The folder is named in Help > About, and deleting it
; is one keystroke for anyone who wants to.

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
    ExecAsOriginalUser(ExpandConstant('{app}\QuillLite.exe'), '', ExpandConstant('{app}'),
      SW_SHOWNORMAL, ewNoWait, LaunchResult);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  LaunchIfChosen(CurPageID);
end;

{ Open QUILL Lite Instead of Notepad (Tools menu) points every Notepad launch at
  this folder's QuillLite.exe through Image File Execution Options. Left behind
  by an uninstall, Notepad would stop opening at all, so the uninstaller takes
  those Debugger values out again: only values naming this install's
  QuillLite.exe, in the parent key and in the Windows 11 per-path subkeys.
  Another program's value, and Microsoft's own values, are left alone. }
const
  NotepadIfeoKey = 'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\notepad.exe';

function DebuggerPointsHere(Key: string): Boolean;
var
  Value: string;
begin
  Result := RegQueryStringValue(HKLM64, Key, 'Debugger', Value) and
    (Pos(Lowercase(ExpandConstant('{app}\QuillLite.exe')), Lowercase(Value)) > 0);
end;

function NotepadKeysPointingHere(var Keys: TArrayOfString): Integer;
var
  Names: TArrayOfString;
  I: Integer;
begin
  SetArrayLength(Keys, 0);
  if DebuggerPointsHere(NotepadIfeoKey) then
  begin
    SetArrayLength(Keys, 1);
    Keys[0] := NotepadIfeoKey;
  end;
  if RegGetSubkeyNames(HKLM64, NotepadIfeoKey, Names) then
    for I := 0 to GetArrayLength(Names) - 1 do
      if DebuggerPointsHere(NotepadIfeoKey + '\' + Names[I]) then
      begin
        SetArrayLength(Keys, GetArrayLength(Keys) + 1);
        Keys[GetArrayLength(Keys) - 1] := NotepadIfeoKey + '\' + Names[I];
      end;
  Result := GetArrayLength(Keys);
end;

<event('CurUninstallStepChanged')>
procedure PutNotepadBack(CurUninstallStep: TUninstallStep);
var
  Keys: TArrayOfString;
  I, ResultCode: Integer;
  Params: string;
begin
  if (CurUninstallStep <> usUninstall) or (NotepadKeysPointingHere(Keys) = 0) then
    Exit;
  if IsAdmin then
  begin
    for I := 0 to GetArrayLength(Keys) - 1 do
      RegDeleteValue(HKLM64, Keys[I], 'Debugger');
  end
  else if not UninstallSilent then
  begin
    { One administrator prompt for every key, the same command the app runs. }
    Params := '/d /s /c "';
    for I := 0 to GetArrayLength(Keys) - 1 do
    begin
      if I > 0 then
        Params := Params + ' & ';
      Params := Params + '"' + ExpandConstant('{sys}\reg.exe') + '" delete "HKLM\' +
        Keys[I] + '" /v Debugger /f /reg:64';
    end;
    Params := Params + '"';
    MsgBox('QUILL Lite is still opening in place of Notepad. To put Notepad back, ' +
      'Windows will ask for administrator approval next.', mbInformation, MB_OK);
    ShellExec('runas', ExpandConstant('{cmd}'), Params, '', SW_HIDE,
      ewWaitUntilTerminated, ResultCode);
  end;
end;
