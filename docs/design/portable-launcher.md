# Portable & Installed Launcher Contract

> **Why this file exists.** Twice now the Windows launcher has broken in a way
> that shipped to users: the bundle-root `quill.exe` could not start. This
> document is the durable contract for how QUILL launches on Windows so the same
> class of bug cannot return unnoticed. The rules below are enforced by tests in
> `tests/unit/scripts/test_build_windows_distribution.py`; if you change the
> packaging, change this doc and those guards together.

## 1. The one invariant

**The `quill.exe` a user clicks must sit in the same directory as the embedded
Python runtime it needs (`python313.dll`, `python313.zip`, `python313._pth`, the
`*.pyd` modules), and it must start QUILL with no command-line arguments.**

`quill.exe` is a byte-for-byte copy of the embeddable distribution's
`pythonw.exe`, re-stamped with QUILL's VERSIONINFO via `rcedit` (so a screen
reader's "what app is this" reads *QUILL for All*, not *Python*). It is
**still just `pythonw.exe`** — it has no idea it should run QUILL, and a bare
`pythonw.exe` double-click does nothing useful. Two things make it work:

1. **Co-location with the runtime.** A Windows executable finds its dependent
   DLLs (`python313.dll`) next to itself. If the runtime is in a `python\`
   subfolder but `quill.exe` is at the bundle root, the root copy is *orphaned*:
   on a clean machine it fails to start; on a machine with a system Python it
   binds to the wrong interpreter and crashes. This is the bug.
2. **A self-run hook.** See §2.

## 2. How `quill.exe` self-runs: `sitecustomize.py`

The build writes a generated `sitecustomize.py` next to the runtime
(`scripts/build_windows_distribution.py` → `_self_run_sitecustomize_source()`,
written in `bundle_embedded_python()` right after the `._pth` is patched to
enable `import site`).

Python auto-imports `sitecustomize` at interpreter startup whenever `site` is
enabled. The hook only acts when the running executable is **`quill.exe`**
(`os.path.basename(sys.executable)`), and then handles two cases:

- **Bare launch** — the argv a double-click produces
  (`len(sys.argv) <= 1 and (not sys.argv or sys.argv[0] == "")`): start QUILL
  with no file.
- **File association** — when QUILL is set as the default app for a document
  type, the OS runs `quill.exe "<path>"`. Because `quill.exe` is a renamed
  `pythonw.exe`, that path arrives as `sys.argv[0]` and Python would otherwise
  try to *run the document as a script*. The hook detects an existing,
  non-`__main__.py` `sys.argv[0]` and forwards it to QUILL as a file to open
  (`sys.argv = ["quill", doc]` then `main()`), so the document opens instead of
  silently doing nothing.

So:

| Invocation | `sitecustomize` branch | Result |
| --- | --- | --- |
| Double-click `quill.exe` | bare launch | QUILL launches (no console, no `-m`) |
| Open a `.docx` with QUILL as default app (`quill.exe "doc.docx"`) | file association | QUILL opens the document |
| `quill.exe -m quill [args]` | no-op (argv[0] is quill's `__main__.py`) | normal `-m quill` runs (shortcuts, file-assoc/verbs the installer registers) |
| `python.exe ...`, `pip ...` (incl. during the build) | no-op | normal Python |

The result is a launcher that needs **no `-m`, no console window, and no `.cmd`
shim** (an earlier `run-quill.cmd` approach was rejected because the console
window flashed on launch). The installer additionally registers its
file-association *open* command and right-click "Send to QUILL" verbs as
`quill.exe -m quill ["%1" | --action <verb> "%1"]` — the `-m quill` is required
because `pythonw` rejects a bare `--action` option and would otherwise run the
file as a script; the `sitecustomize` file-association branch above is the safety
net for associations a user sets manually (whose command is just
`quill.exe "%1"`).

## 3. The layout: flat, not nested

The portable bundle and the installed app both use a **flat** layout — the
embedded runtime is unpacked at the bundle/install root, beside `quill.exe`:

```
<bundle root>/
  quill.exe            <- self-runs (stamped pythonw.exe + sitecustomize)
  pythonw.exe  python.exe  python313.dll  python313.zip  python313._pth
  sitecustomize.py
  Lib/  Scripts/       <- runtime stdlib + site-packages (incl. quill)
  data/                <- portable-mode data target (ships with a keep-file)
  docs/  tools/  vendor/  kokoro-models/
  manifest.json  README.txt
```

The build stages the runtime into a temporary `python\` subfolder and then
**flattens it to the root** (`build_windows_distribution()`, the
`for entry in sorted(staged_runtime.iterdir())` move). The runtime ships none of
the bundle's own entries (`data/`, `docs/`, `tools/`, `vendor/`,
`kokoro-models/`, `manifest.json`, `README.txt`), so the move cannot clobber
them — and a future name collision raises rather than overwriting.

The installer is generated **from** the portable bundle
(`[Files] Source: "..\portable\*" -> {app}`), so the installed app inherits the
flat layout automatically. `BundledLauncherPath` in the `[Code]` section resolves
`{app}\quill.exe`, then `{app}\pythonw.exe` — **never a `{app}\python\` path**.

### Why not nested (the history)

- **#615** introduced the VERSIONINFO-stamped `quill.exe` and nested the runtime
  under `python\`, hoisting an orphaned copy of `quill.exe` to the bundle root as
  a "portable-evidence marker." That root copy could not load the interpreter.
- **#722** fixed the *installer shortcuts* to launch `python\quill.exe -m quill`,
  so installed users were fine — but the *portable* double-click still landed on
  the orphaned root `quill.exe` and did nothing. Portable users were stuck.
- The fix (this contract) **flattens the runtime to the root** so the click
  target is no longer orphaned, and adds the `sitecustomize` self-run hook so no
  `-m` and no `.cmd` are needed.

### Upgrading over a pre-flatten (nested) install

Inno Setup only *overlays* new `[Files]`; it never removes files a previous
install left behind. So installing the flat build over an old nested install
would otherwise leave two messes, both handled by the generator:

- **Stale `{app}\python` runtime tree** (~150 MB plus a second, dead `quill.exe`).
  The `[InstallDelete]` section wipes `{app}\python` on install. It holds no user
  data (that lives in `%APPDATA%\Quill`, or `{app}\data` for portable), so the
  wipe is always safe; on a clean or already-flat install the dir is absent and
  it is a no-op. The live flat runtime at the `{app}` root is *not* wiped — it is
  overwritten in place by the `ignoreversion` `[Files]` copy.
- **A desktop shortcut pointing at a launcher that no longer exists.** An old
  shortcut targeted `run-quill.cmd` (beta 1) or the nested `python\quill.exe`;
  after the upgrade both are gone, so the shortcut would be dead. The
  `CurStepChanged(ssInstall)` hook deletes the stale `{autodesktop}\<App>.lnk`
  before `[Icons]` recreates it pointing at the flat `{app}\quill.exe` (via
  `BundledLauncherPath`). The Start-Menu shortcut is recreated by `[Icons]` on
  every install, so it refreshes automatically.

**Portable upgraders** should extract the new zip to a *fresh* folder rather than
on top of an old one — there is no installer to run the `{app}\python` cleanup,
so an extract-over-old would leave the stale `python\` subfolder beside the new
flat runtime. It is harmless (the flat `quill.exe` ignores it), but it is clutter
and confusing. The README advises a clean extract.

## 4. Portable-mode detection depends on this

`quill.core.storage_mode._has_portable_evidence` marks a bundle "portable" when
the anchor has **`quill.exe` + a sibling `data/`** folder. Therefore:

- `data/` **must ship in the bundle** and must survive zipping. Archivers drop
  empty directories, so the build writes a `data/README.txt` keep-file. Without
  it, an unzipped bundle could lose `data/` and silently stop being recognized as
  portable.
- `_resolve_app_root` walks up from `sys.executable`, so it still resolves
  correctly whether `quill.exe` runs from the root (flat) — the supported
  layout — or, defensively, one level down.

## 5. Regression guards (do not remove)

In `tests/unit/scripts/test_build_windows_distribution.py`:

- `test_bundled_launcher_resolves_flat_self_running_quill_exe` — `BundledLauncherPath`
  prefers `{app}\quill.exe`, then `{app}\pythonw.exe`, and uses no `python\` path.
- `test_installer_script_has_no_nested_python_launcher_path` — the whole `.iss`
  contains no `{app}\python\` string.
- `test_self_run_sitecustomize_launches_quill_for_a_bare_exe` — the generated
  `sitecustomize.py` guards on `quill.exe` + bare argv and calls
  `quill.__main__:main`.
- `test_self_run_sitecustomize_opens_file_associations` — the hook forwards an
  OS-passed document (`quill.exe "doc"`) to QUILL via `argv` instead of running
  it as a script.
- `test_shell_verb_command_launches_quill_exe_with_action` — the installer's
  open/verb commands pass `-m quill` so `pythonw` runs QUILL, not the file.
- `test_portable_bundle_flattens_runtime_to_root` — a built portable bundle has
  `quill.exe`, `sitecustomize.py`, `python313.dll`, and `Lib/...` at the root,
  **no `python\` subdir**, and a `data/` folder.
- `test_installer_clean_replaces_first_party_package_for_safe_upgrades` — the
  `[InstallDelete]` clean-replace targets `{app}\Lib\site-packages\quill` (flat).
- `test_committed_installer_iss_is_in_sync_with_generator` — `installer/quill.iss`
  is the exact generator output; regenerate it when the generator changes.

## 6. Manual verification before a release

After building (or before re-uploading a portable zip):

1. Unzip the portable bundle to a fresh folder.
2. Confirm there is **no `python\` subfolder**, and `quill.exe`, `sitecustomize.py`,
   `python313.dll`, and `data\` are all at the root.
3. **Double-click `quill.exe`** — QUILL must open with no console window and no
   arguments. (`python.exe -m quill --version` from the root is a good non-GUI
   smoke check that the flat runtime loads.)
4. For the installer: install, then launch from the Start Menu shortcut **and**
   by double-clicking `{app}\quill.exe` directly — both must work.

## 7. Things that will re-break this — don't

- Re-nesting the runtime under `python\` while leaving `quill.exe` at the root.
- Hoisting/placing a `quill.exe` anywhere the runtime is not beside it.
- Removing `sitecustomize.py` generation, or relying on `-m quill` in shortcuts
  as the *only* launch mechanism (it does not help a bare double-click).
- Shipping an empty `data/` with no keep-file (it can vanish on zip/unzip).
- Hand-editing `installer/quill.iss` (it is generated; edit
  `build_inno_setup_script()` and regenerate).
