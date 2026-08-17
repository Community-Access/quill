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
; and its [Icons]/[Run] should launch the app via:
;   {code:RuntimeExe} -m <the app's module>     (e.g. -m quill.apps.radio)

[Files]
; The payload's own marker, extracted to {tmp} before anything is copied, so
; RuntimeNeedsInstall can compare the build this setup CARRIES against the
; build already installed. Without it the check could only see one side.
Source: "{#RuntimeSourceDir}\quillville-runtime.json"; Flags: dontcopy noencryption
; The whole runtime, gated by RuntimeNeedsInstall so a second app skips it.
Source: "{#RuntimeSourceDir}\*"; DestDir: "{code:RuntimeDir}"; Components: runtime; \
  Check: RuntimeNeedsInstall; \
  Flags: ignoreversion recursesubdirs createallsubdirs uninsneveruninstall

[Run]
; Record that this app needs this runtime version (idempotent). Runs the shared
; runtime's own Python so the tested refcount logic (runtime_cli) does the work.
Filename: "{code:RuntimeExe}"; Parameters: "-m quill.core.runtime_cli register {#AppRefId} {#RuntimeVersion}"; \
  StatusMsg: "Registering the shared runtime..."; Flags: runhidden waituntilterminated

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
