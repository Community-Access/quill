; QuillLite installer -- shared-runtime layout.
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
; QuillLite is the leanest app in the family after Weather -- one editor
; control, six small windows, no ffmpeg and no libmpv -- so the per-app payload
; is just the icon, the C launcher, and (optionally) the docs.
;
; Build inputs (must exist before ISCC runs):
;   - the shared runtime at ..\..\runtime\dist\QuillVilleRuntime
;     (built by ..\..\runtime\quillville-runtime.spec, marker stamped;
;     build_runtime.ps1 chains the spec, the marker stamp, and the staging);
;   - the per-app QuillLite.exe at ..\dist\QuillLite\QuillLite.exe
;     (built by build_native_launcher.py);
;   - the per-app icon at ..\assets\quill-lite.ico;
;   - the rendered QuillLite docs at ..\dist\QuillLite\docs.

#define AppName "QuillLite"
; Version is single-sourced from build_release.ps1, which passes
; /dAppVersion=<version> to ISCC. The literal below is only the fallback for a
; manual ISCC run and must be kept in step with build_release.ps1's $version.
#ifndef AppVersion
  #define AppVersion "1.0.0"
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
VersionInfoVersion=1.0.0.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} accessible plain text and rich text editor (shared runtime)
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
Name: "assoc"; Description: "Open .txt and .rtf files with {#AppName}"; Types: custom

[Files]
Source: "..\assets\quill-lite.ico"; DestDir: "{app}"; Components: main; Flags: ignoreversion
Source: "..\dist\QuillLite\QuillLite.exe"; DestDir: "{app}"; Components: main; Flags: ignoreversion
; The updater reads this to offer the right edition back (core/install_edition.py).
Source: "..\installer\edition-installer-full.txt"; DestDir: "{app}"; DestName: "quill-edition.txt"; Components: main; Flags: ignoreversion
Source: "..\dist\QuillLite\docs\*"; DestDir: "{app}\docs"; Components: docs; Flags: ignoreversion recursesubdirs createallsubdirs

; The shared runtime (install-if-absent) + reference registration + orphan
; removal on uninstall. Defines RuntimeDir/RuntimeExe used by [Icons]/[Run].
#include "..\..\..\installer\shared-runtime.iss"

[Icons]
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
; Harmless for QuillLite from now on, because QuillLite publishes no Companion
; zip and the updater falls through to this installer -- the right answer by
; luck rather than by design. The two meanings of "app root" need separating
; before it is right on purpose.
Name: "{group}\{#AppName}"; Filename: "{app}\QuillLite.exe"; IconFilename: "{app}\quill-lite.ico"; Components: main
Name: "{group}\{#AppName} User Guide"; Filename: "{app}\docs\userguide.html"; Components: docs
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\QuillLite.exe"; IconFilename: "{app}\quill-lite.ico"; Tasks: desktopicon; Components: main

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Registry]
; "Open with QuillLite" on .txt and .rtf, as an OPTIONAL component and never as
; the default handler. A text editor that quietly takes over every .txt on the
; machine is a text editor people uninstall; taking the verb rather than the
; association leaves Notepad, WordPad and QUILL exactly where they were.
Root: HKA; Subkey: "Software\Classes\Applications\QuillLite.exe\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\QuillLite.exe"" ""%1"""; Flags: uninsdeletekey; Components: assoc
Root: HKA; Subkey: "Software\Classes\Applications\QuillLite.exe"; ValueType: string; ValueName: "FriendlyAppName"; ValueData: "{#AppName}"; Flags: uninsdeletekey; Components: assoc
Root: HKA; Subkey: "Software\Classes\Applications\QuillLite.exe\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\quill-lite.ico"; Flags: uninsdeletekey; Components: assoc
Root: HKA; Subkey: "Software\Classes\.txt\OpenWithList\QuillLite.exe"; Flags: uninsdeletekey; Components: assoc
Root: HKA; Subkey: "Software\Classes\.rtf\OpenWithList\QuillLite.exe"; Flags: uninsdeletekey; Components: assoc
; QuillLite edits four kinds, not two. Markdown and HTML were missing from
; this list until 2026-09-16 -- so a .md file could not reach the editor that
; has a Markdown mode, from the menu Windows offers for exactly that (bad.md A1).
Root: HKA; Subkey: "Software\Classes\.md\OpenWithList\QuillLite.exe"; Flags: uninsdeletekey; Components: assoc
Root: HKA; Subkey: "Software\Classes\.markdown\OpenWithList\QuillLite.exe"; Flags: uninsdeletekey; Components: assoc
Root: HKA; Subkey: "Software\Classes\.html\OpenWithList\QuillLite.exe"; Flags: uninsdeletekey; Components: assoc
Root: HKA; Subkey: "Software\Classes\.htm\OpenWithList\QuillLite.exe"; Flags: uninsdeletekey; Components: assoc

[Run]
Filename: "{app}\QuillLite.exe"; Description: "Launch {#AppName}"; Flags: postinstall nowait skipifsilent unchecked

[UninstallDelete]
; Remove only QuillLite's own {app} payload. The shared runtime is left to the
; fragment's CurUninstallStepChanged, which deletes it only when unreferenced.
Type: filesandordirs; Name: "{app}"

; %LOCALAPPDATA%\QuillLite -- settings, recent files, and any recovered work --
; is deliberately NOT removed. Recovery slots are the one thing in that folder
; somebody may not have finished with, and an uninstaller is the worst possible
; moment to discover that. The folder is named in Help > About, and deleting it
; is one keystroke for anyone who wants to.
