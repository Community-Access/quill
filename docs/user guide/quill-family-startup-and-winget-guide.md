# Starting QuillVille apps with Windows and installing with WinGet

**Documentation draft:** the start-minimized controls are implemented in the
working tree. WinGet package IDs below are proposals, and no QuillVille package
has been accepted into the WinGet catalog yet. Do not publish the install
commands until the package pull requests have been approved and merged.

## Start an app minimized at sign-in

On an installed Windows copy, turn on both the app's **Start with Windows**
setting and its **Start minimized when Windows starts** setting. The second
setting changes only the way that login launch appears. Opening the app from the
Start menu, a file, or another app continues to show its normal window.

| App | Where to choose the settings |
| --- | --- |
| QUILL | **Settings > General**: check **Start QUILL when Windows starts** and **Start QUILL minimized when Windows starts**. Background mode is enabled automatically so the tray icon can reopen the editor. |
| Quill Radio | **Preferences (Ctrl+,)**: check **Start Quill Radio with Windows** and **Start Quill Radio minimized when Windows starts**. |
| QUILL Cast | **Preferences (Ctrl+,)**: check **Start QUILL Cast with Windows** and **Start QUILL Cast minimized when Windows starts**. |
| Quill Weather | **Options**: check **Start Quill Weather with Windows** and **Start minimized when Windows starts**. |
| Quill Inkwell | **Options**: check **Start Quill Inkwell with Windows** and **Start minimized when Windows starts**. |
| QUILL Transcribe | **Options**: check **Start QUILL Transcribe with Windows** and **Start minimized when Windows starts**. |

To show the window at sign-in, leave **Start with Windows** on and turn off
**Start minimized when Windows starts**. To stop automatic launch entirely,
turn off **Start with Windows**. Both settings apply to the current Windows
account and need no administrator rights. Portable copies cannot create startup
entries; use an installed copy for these options. If Windows hides the tray
icon, open the notification-area settings and show the app there so you have a
visible way to bring it back.

QUILL Transcribe may still show its setup window on a first launch before
dictation setup is complete. Start minimized does not skip required setup or
start dictation by itself.

## Install or update with WinGet

The following IDs are being prepared for the public WinGet catalog:

- `CommunityAccess.QuillLite`
- `CommunityAccess.QuillRadio`
- `CommunityAccess.Quill` and the other family IDs are proposals for later
  Stable releases.

No package is published yet. Once an app's package has been accepted, its
release page and this guide will be updated with the approved ID. The command
will then be:

```powershell
winget install --id <approved-package-id> --exact
```

QuillVille apps have their own updater. To update a specific app deliberately
through WinGet, name its approved ID:

```powershell
winget upgrade --id <approved-package-id> --exact
```

To remove it through WinGet:

```powershell
winget uninstall --id <approved-package-id> --exact
```

The WinGet package will target the signed, installed Setup edition. Portable
ZIPs, beta builds and the shared runtime are not WinGet packages. The package
manifest will prevent an automatic WinGet upgrade from racing with an app's
own updater; a named upgrade remains available.

For maintainers adding a new app or preparing its next Stable release, follow
the [WinGet deployment guide](../planning/winget.md). It covers package ID
approval, the app catalogue, release tags, manifest generation, validation,
Sandbox testing and the guarded public submission process.
