; Shared QuillVille Runtime -- includable Inno Setup fragment.
;
; The shared runtime (one CPython + wxPython + the shared packages, built by
; standalone\runtime\quillville-runtime.spec) is installed ONCE per user and
; reused by every QuillVille app. An app installer includes this fragment to:
;   1. install the runtime into {localappdata}\QuillVille\Runtime, but ONLY when
;      a matching version is not already there (a sibling app installed it);
;   2. register this app's reference so the runtime survives until the last app
;      that needs it is uninstalled (quill.core.runtime_cli -> runtime_refs);
;   3. remove the shared runtime on uninstall only when it becomes unreferenced.
;
; The app installer must define these BEFORE #include-ing this file:
;   #define RuntimeVersion   "3.13.1"     ; the CPython version the runtime ships
;   #define RuntimeSourceDir "..\..\runtime\dist\QuillVilleRuntime"  ; built payload
;   #define AppRefId         "radio"      ; this app's stable id in runtime_refs
; and, for a media app, one define per tool it declares in REQUIRED_COMPONENTS:
;   #define ToolFfmpeg                    ; quill.apps.radio declares "ffmpeg"
;   #define ToolMpv                       ; ...and "mpv"
; plus, for an app that plays YouTube (Radio), the JavaScript runtime yt-dlp
; solves YouTube's challenges with, and for Radio the OptiLab Core adapter:
;   #define ToolDeno                      ; tools\deno\deno.exe + DENO-LICENSE.txt
;   #define ToolOptiLab                   ; quill-optilab.exe + its LICENSE/NOTICE
; and its [Icons]/[Run] should launch the app via:
;   {code:RuntimeExe} -m <the app's module>     (e.g. -m quill.apps.radio)

[Files]
; The payload's own marker, extracted to {tmp} before anything is copied, so
; RuntimeNeedsInstall can compare the build this setup CARRIES against the
; build already installed. Without it the check could only see one side.
Source: "{#RuntimeSourceDir}\quillville-runtime.json"; Flags: dontcopy noencryption
; The runtime itself, gated by RuntimeNeedsInstall so a second app skips it.
; tools\ and the OptiLab adapter are excluded here and installed
; unconditionally below -- see why.
Source: "{#RuntimeSourceDir}\*"; DestDir: "{code:RuntimeDir}"; Components: runtime; \
  Excludes: "tools,tools\*,quill-optilab.exe,OptiLabCore-LICENSE.txt,OptiLabCore-NOTICE.txt"; \
  Check: RuntimeNeedsInstall; \
  Flags: ignoreversion recursesubdirs createallsubdirs uninsneveruninstall

; -- the media tools, installed in EVERY order ------------------------------
;
; WHY THESE ARE NOT GATED BY RuntimeNeedsInstall
; ----------------------------------------------
; The runtime is one shared thing; the media tools beside it are contributed
; per app (scripts\StageMediaTools.ps1), because ffmpeg + libmpv are 306 MB and
; four of the seven apps never call them. Those two facts used to meet in one
; [Files] line: tools\ rode along inside the gated runtime wildcard, so whether
; a machine ended up with libmpv depended on the ORDER the apps were installed
; in. Install Cast (ffmpeg only, newer runtime build) and then Radio (ffmpeg +
; mpv, older build) and Radio's whole payload was skipped -- mpv never landed,
; Radio dropped to Windows Media, and it lost Ogg/Opus/HLS stations, output
; device selection and the DVR buffer. Reinstalling could not fix it either:
; the reinstall hit the same skip, which made media_health's "reinstalling
; restores it" advice untrue in exactly the case it was written for.
;
; So the tools are their own entries with no Check. Each app always lays down
; what it declares, whoever installed first, and a machine's tools become the
; UNION of what its apps need rather than whatever the newest runtime build
; happened to carry. It costs install-time copying and nothing in download
; size -- these bytes are already in this installer's payload -- and it is what
; makes a media app repairable by reinstalling it, on its own, in any order.
;
; ignoreversion + the same-content payload make a repeat install a no-op copy.
; An app that declares no media tools defines neither symbol and ships none,
; which also stops it silently packing 306 MB another app's build happened to
; leave in the communal runtime dist.
; Pinned by tests\unit\structure\test_shared_runtime_installer.py.
#ifdef ToolFfmpeg
#pragma message "shared-runtime: packing tools\ffmpeg (this app declares ffmpeg)"
Source: "{#RuntimeSourceDir}\tools\ffmpeg\*"; DestDir: "{code:RuntimeDir}\tools\ffmpeg"; \
  Components: runtime; \
  Flags: ignoreversion recursesubdirs createallsubdirs uninsneveruninstall
#endif
#ifdef ToolMpv
#pragma message "shared-runtime: packing tools\mpv (this app declares mpv)"
Source: "{#RuntimeSourceDir}\tools\mpv\*"; DestDir: "{code:RuntimeDir}\tools\mpv"; \
  Components: runtime; \
  Flags: ignoreversion recursesubdirs createallsubdirs uninsneveruninstall
#endif
; deno: yt-dlp's JavaScript runtime for YouTube's signature and "n" challenges
; (quill.core.js_runtime.find_deno). Same reasoning as the tools above --
; ungated, or a second app installed after a newer runtime would skip it and
; YouTube would degrade with nothing downloaded to repair it (2026-09-27).
#ifdef ToolDeno
#pragma message "shared-runtime: packing tools\deno (this app plays YouTube)"
Source: "{#RuntimeSourceDir}\tools\deno\*"; DestDir: "{code:RuntimeDir}\tools\deno"; \
  Components: runtime; \
  Flags: ignoreversion recursesubdirs createallsubdirs uninsneveruninstall
#endif
; The OptiLab Core adapter sits beside QuillVilleRuntime.exe (where
; exact_optilab looks), so it used to ride inside the gated runtime wildcard
; and a second app skipped it -- exactly the install-order trap the tools had.
#ifdef ToolOptiLab
#pragma message "shared-runtime: packing quill-optilab.exe (this app declares OptiLab)"
Source: "{#RuntimeSourceDir}\quill-optilab.exe"; DestDir: "{code:RuntimeDir}"; \
  Components: runtime; \
  Flags: ignoreversion uninsneveruninstall
Source: "{#RuntimeSourceDir}\OptiLabCore-LICENSE.txt"; DestDir: "{code:RuntimeDir}"; \
  Components: runtime; \
  Flags: ignoreversion uninsneveruninstall
Source: "{#RuntimeSourceDir}\OptiLabCore-NOTICE.txt"; DestDir: "{code:RuntimeDir}"; \
  Components: runtime; \
  Flags: ignoreversion uninsneveruninstall
#endif

[Run]
; Record that this app needs this runtime version (idempotent). Runs the shared
; runtime's own Python so the tested refcount logic (runtime_cli) does the work.
Filename: "{code:RuntimeExe}"; Parameters: "-m quill.core.runtime_cli register {#AppRefId} {#RuntimeVersion}"; \
  StatusMsg: "Registering the shared runtime..."; Flags: runhidden waituntilterminated
; Repair a "start with Windows" entry an older build wrote as the bare runtime
; exe. The app repairs its own entry at launch, but that needs a launch -- and
; this is the entry that PREVENTS one: before 3.0.2 the bare runtime met the
; listener with PyInstaller's "Unhandled exception in script" box at every
; login, and nothing suggested that opening the app by hand would cure it
; (reported 2026-09-29). {app} is passed so the repaired entry names this app's
; native launcher, whose path survives a runtime upgrade. Always exits 0, so a
; locked-down registry costs the repair and not the install.
Filename: "{code:RuntimeExe}"; Parameters: "-m quill.core.runtime_cli heal-launch-entries ""{app}"""; \
  StatusMsg: "Checking the startup entry..."; Flags: runhidden waituntilterminated

[Code]
function RuntimeMajor(): string;
var
  Version: string;
  Dot: Integer;
begin
  // "3.13.14" -> "3.13": the runtime is keyed by MAJOR, never overwritten in
  // place, so a future Python major lands alongside rather than on top of it.
  Version := '{#RuntimeVersion}';
  Dot := Pos('.', Version);
  if Dot = 0 then begin Result := Version; exit; end;
  Result := Copy(Version, 1, Dot);
  Version := Copy(Version, Dot + 1, Length(Version));
  Dot := Pos('.', Version);
  if Dot = 0 then Result := Result + Version
  else Result := Result + Copy(Version, 1, Dot - 1);
end;

function RuntimeDir(Param: string): string;
begin
  // MUST match the launcher: quill/native/launcher/runtime_resolve.c probes
  // %LOCALAPPDATA%\QuillVille\Runtime\<major>\quillville-runtime.json, and
  // the design's side-by-side-by-major rule depends on that segment. This
  // installed to the UNVERSIONED folder, so a fresh install laid the runtime
  // somewhere the launcher never looks and the app could not start at all --
  // "Quill Radio could not find a Python runtime" (found 2026-08-16).
  // tests/unit/structure/test_shared_runtime_installer.py pins the agreement.
  Result := ExpandConstant('{localappdata}\QuillVille\Runtime') + '\' + RuntimeMajor();
end;

function RuntimeExe(Param: string): string;
begin
  Result := RuntimeDir('') + '\QuillVilleRuntime.exe';
end;

// Read one value out of a quillville-runtime.json marker with plain string ops
// (the marker is a tiny, fixed-shape JSON object, so a full parser is overkill
// and would not be available in Pascal anyway). '' when absent or unreadable.
function MarkerValue(MarkerFile, Key: string): string;
var
  Content: AnsiString;
  Text, Quoted: string;
  P, Q: Integer;
begin
  Result := '';
  if not FileExists(MarkerFile) then
    exit;
  if not LoadStringFromFile(MarkerFile, Content) then
    exit;
  Text := String(Content);
  Quoted := '"' + Key + '"';
  P := Pos(Quoted, Text);
  if P = 0 then
    exit;
  // Move past the key and its colon to the opening quote of the value.
  Text := Copy(Text, P + Length(Quoted), Length(Text));
  P := Pos('"', Text);
  if P = 0 then
    exit;
  Text := Copy(Text, P + 1, Length(Text));
  Q := Pos('"', Text);
  if Q = 0 then
    exit;
  Result := Copy(Text, 1, Q - 1);
end;

function InstalledMarkerFile(): string;
begin
  Result := RuntimeDir('') + '\quillville-runtime.json';
end;

function InstalledRuntimeVersion(): string;
begin
  Result := MarkerValue(InstalledMarkerFile(), 'python');
end;

// The [Files] Check: install the shared runtime unless what is already there is
// the same CPython AND at least as new as the payload this setup carries.
//
// The version-only test this replaced was the whole bug: the runtime carries
// the entire `quill` package -- every app's actual code -- so two builds on the
// same CPython are NOT interchangeable. An update installed beside an existing
// runtime skipped the copy and the app kept running the old code, with the
// installer reporting success (#1217 was the same fault with a coarser
// symptom; the build id gained time granularity here so two builds on one day
// are no longer indistinguishable).
//
// Newer-or-equal installed build is left alone, so installing an older sibling
// app never downgrades the shared runtime. An unreadable or missing build on
// either side means install: correctness beats bandwidth.
// Mirrors quill.core.runtime_marker.needs_install, which is unit-tested.
var
  gRuntimeChecked: Boolean;
  gRuntimeNeeded: Boolean;

function RuntimeNeedsInstall(): Boolean;
var
  PayloadBuild, InstalledBuild: string;
begin
  if not gRuntimeChecked then
  begin
    gRuntimeChecked := True;
    gRuntimeNeeded := True;
    if InstalledRuntimeVersion() = '{#RuntimeVersion}' then
    begin
      ExtractTemporaryFile('quillville-runtime.json');
      PayloadBuild := MarkerValue(
        ExpandConstant('{tmp}\quillville-runtime.json'), 'build');
      InstalledBuild := MarkerValue(InstalledMarkerFile(), 'build');
      // Build ids are sortable stamps (yyyy-mm-ddThh:mm:ssZ), so a plain
      // string compare orders them.
      if (PayloadBuild <> '') and (InstalledBuild <> '')
         and (InstalledBuild >= PayloadBuild) then
        gRuntimeNeeded := False;
    end;
  end;
  Result := gRuntimeNeeded;
end;

// On uninstall: drop this app's reference. runtime_cli exits 10 when the runtime
// is now unreferenced -- then, and only then, remove the shared runtime folder.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if FileExists(RuntimeExe('')) then
    begin
      if Exec(RuntimeExe(''),
              '-m quill.core.runtime_cli unregister {#AppRefId} {#RuntimeVersion}',
              '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      begin
        if ResultCode = 10 then
          DelTree(RuntimeDir(''), True, True, True);
      end;
    end;
  end;
end;
