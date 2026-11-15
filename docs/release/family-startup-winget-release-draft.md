# QuillVille family: start minimized and WinGet (release draft)

**Not for publication yet.** Package IDs remain proposals, no WinGet package
has been submitted, and the release version/date must be filled in after the
app-specific Stable releases are chosen.

## Start minimized when Windows starts

QUILL, Quill Radio, QUILL Cast, Quill Weather, Quill Inkwell and QUILL
Transcribe can now start with Windows without opening their main window. Turn
on the app's existing **Start with Windows** setting, then choose **Start
minimized when Windows starts**. The app remains available from the system
tray. This choice affects only sign-in; starting the app normally still opens
its window. Portable copies do not add Windows startup entries.

For QUILL Transcribe, the first launch still presents any required setup before
the app can stay minimized. Starting at sign-in never begins dictation.

## WinGet packages in preparation

WinGet manifest drafts are being prepared for the signed, installed editions
of QUILL Lite and Quill Radio. The packages will use permanent publisher
approved IDs, exact versioned release assets, and their SHA-256 hashes. The
app's own updater remains in control of automatic updates; users will be able
to request a named WinGet upgrade after the packages are accepted.

Do not include a WinGet install command in public release notes until the
package pull request has merged and the package is visible in the catalog.
