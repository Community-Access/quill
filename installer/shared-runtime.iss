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
function RuntimeDir(Param: string): string;
begin
  Result := ExpandConstant('{localappdata}\QuillVille\Runtime');
end;

function RuntimeExe(Param: string): string;
begin
  Result := RuntimeDir('') + '\QuillVilleRuntime.exe';
end;

// Extract the "python" value from the runtime's quillville-runtime.json marker
// with plain string ops (the marker is a tiny, fixed-shape JSON object, so a
// full parser is overkill and would not be available in Pascal anyway).
function InstalledRuntimeVersion(): string;
var
  MarkerFile: string;
  Content: AnsiString;
  Text, Key: string;
  P, Q: Integer;
begin
  Result := '';
  MarkerFile := RuntimeDir('') + '\quillville-runtime.json';
  if not FileExists(MarkerFile) then
    exit;
  if not LoadStringFromFile(MarkerFile, Content) then
    exit;
  Text := String(Content);
  Key := '"python"';
  P := Pos(Key, Text);
  if P = 0 then
    exit;
  // Move past the key and its colon to the opening quote of the value.
  Text := Copy(Text, P + Length(Key), Length(Text));
  P := Pos('"', Text);
  if P = 0 then
    exit;
  Text := Copy(Text, P + 1, Length(Text));
  Q := Pos('"', Text);
  if Q = 0 then
    exit;
  Result := Copy(Text, 1, Q - 1);
end;

// The [Files] Check: install the runtime only when the wanted version is not
// already present. Cached so it is not recomputed for every file.
var
  gRuntimeChecked: Boolean;
  gRuntimeNeeded: Boolean;

function RuntimeNeedsInstall(): Boolean;
begin
  if not gRuntimeChecked then
  begin
    gRuntimeNeeded := (InstalledRuntimeVersion() <> '{#RuntimeVersion}');
    gRuntimeChecked := True;
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
