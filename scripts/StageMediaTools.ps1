# Stage the media tools an app declares into the shared QuillVille Runtime.
#
# WHY THIS IS NOT IN build_runtime.ps1
# ------------------------------------
# It used to be, and that put ffmpeg + ffprobe + libmpv -- 304 MB, 41% of the
# runtime -- into every app that installs the runtime, including the four that
# never call them. Quill Weather's installer was 191 MB to read out a forecast.
#
# The 2026-07-20 runtime/component plan (S2) puts the media tools beside the
# runtime, not inside it, and the app layer already declares who needs what:
#   quill.apps.radio / .studio REQUIRED_COMPONENTS = ("ffmpeg", "mpv")
#   quill.apps.podcasts                             = ("ffmpeg",)
#   weather, inkwell, beacon, social, converter, player: nothing.
# So each media app's own build_release.ps1 stages exactly what it declares,
# after the shared runtime is built. An app that declares nothing calls nothing
# and ships a runtime 304 MB lighter -- with no per-app opt-out list to keep in
# step, because staging is opt-IN.
#
# The apps that DO need the tools are no bigger than before and keep working
# offline the moment their installer finishes: the tools are still inside the
# installer payload, just contributed by the app rather than by the runtime.
# They land in the runtime's tools\ directory, which is exactly where
# quill.core.speech.ffmpeg.ffmpeg_search_dirs and mpv_engine.find_libmpv
# already look (via QUILL_APP_ROOT), so no runtime code changes at all.
#
# This mirrors how the OptiLab Core adapter is already staged into the shared
# runtime by the app build script rather than by the runtime build.
#
# SECURITY: both directories are copied verbatim into a shipped artifact, so
# they must be vetted staging directories passed explicitly by the caller.
# Neither this script nor build_runtime.ps1 will resolve ffmpeg from the
# builder's PATH or libmpv from the user-writable
# %APPDATA%\Quill\engine-packs\mpv: either could be poisoned by a stale or
# malicious local file and would then be planted, unverified, into the runtime
# every QuillVille app on the machine shares.

function Stage-QuillMediaTools {
    [CmdletBinding()]
    param(
        # The built shared runtime (dist\QuillVilleRuntime) to stage into.
        [Parameter(Mandatory = $true)][string]$RuntimeDist,
        # A vetted directory holding ffmpeg.exe (and optionally ffprobe.exe).
        [string]$FfmpegDir = "",
        # A vetted directory holding libmpv-2.dll. Omit for apps that declare
        # only ffmpeg (Cast) -- 110 MB they have no use for. Radio and Studio
        # both declare mpv: Radio as its playback engine, Studio for the
        # player preview its build has always bundled.
        [string]$LibmpvDir = "",
        # A vetted directory holding deno.exe and DENO-LICENSE.txt
        # (scripts\fetch_build_deps.py --only deno). yt-dlp's JavaScript runtime
        # for YouTube's challenges; staged by the app that plays YouTube
        # (Radio), found by quill.core.js_runtime.find_deno.
        [string]$DenoDir = "",
        # A vetted directory holding the Copilot hostless runtime bundle
        # (scripts\fetch_build_deps.py --only copilot): copilot.exe (the SDK's
        # compatibility alias), copilot-runtime.exe, runtime.node, the
        # .hostless-runtime-assets-v2 marker, the runtime assets in subfolders,
        # and COPILOT-CLI-LICENSE.txt. The GitHub Copilot CLI the Copilot SDK
        # drives. Unlike the tools above it is not per app: it ships in every
        # shared runtime, so build_runtime.ps1 stages it. The whole folder is
        # copied unmodified -- the licence allows redistribution only that way,
        # and only with the licence beside it.
        [string]$CopilotDir = "",
        # A vetted directory holding codex-app-server.exe, CODEX-LICENSE.txt and
        # CODEX-NOTICE.txt (scripts\fetch_build_deps.py --only codex). OpenAI's
        # Codex app-server, found by quill.core.ai.codex_binary; staged by
        # build_runtime.ps1 into every shared runtime, unmodified.
        [string]$CodexDir = ""
    )

    if (-not (Test-Path (Join-Path $RuntimeDist "QuillVilleRuntime.exe"))) {
        throw "Stage-QuillMediaTools: '$RuntimeDist' is not a built shared runtime."
    }

    if ($FfmpegDir) {
        $source = Join-Path $FfmpegDir "ffmpeg.exe"
        if (-not (Test-Path $source)) {
            throw "ffmpeg.exe not found in -FfmpegDir '$FfmpegDir'."
        }
        $target = Join-Path $RuntimeDist "tools\ffmpeg"
        New-Item -ItemType Directory -Force $target | Out-Null
        Copy-Item $source $target -Force
        # ffprobe is NOT optional dead weight: it reads M4B/M4A chapter marks
        # for audiobooks and measures track durations. Dropping it breaks
        # chaptered audiobooks in Cast and Studio.
        $ffprobe = Join-Path $FfmpegDir "ffprobe.exe"
        if (Test-Path $ffprobe) { Copy-Item $ffprobe $target -Force }
        # This FFmpeg build is GPLv3: its licence and source offer ship beside
        # it, as mpv's do. One copy lives in the package (quill\data\notices\
        # ffmpeg), which QUILL's own on-demand install writes out as well,
        # because the pinned zip's own copies are not extracted.
        $notices = Join-Path $PSScriptRoot "..\quill\data\notices\ffmpeg"
        $noticeFiles = @(Get-ChildItem $notices -File -Filter *.txt -ErrorAction SilentlyContinue)
        if ($noticeFiles.Count -lt 2) {
            throw "FFmpeg licence notices not found in '$notices' -- FFmpeg ships with its licence."
        }
        $noticeFiles | ForEach-Object { Copy-Item $_.FullName $target -Force }
        Write-Host "Staged ffmpeg and its licence notices into the shared runtime."
    }

    if ($LibmpvDir) {
        $source = Join-Path $LibmpvDir "libmpv-2.dll"
        if (-not (Test-Path $source)) {
            throw "libmpv-2.dll not found in -LibmpvDir '$LibmpvDir'."
        }
        $target = Join-Path $RuntimeDist "tools\mpv"
        New-Item -ItemType Directory -Force $target | Out-Null
        Copy-Item $source $target -Force
        # mpv is LGPL/GPL: its licence and source-offer texts ship beside it.
        Get-ChildItem $LibmpvDir -File -Filter *.txt -ErrorAction SilentlyContinue |
            ForEach-Object { Copy-Item $_.FullName $target -Force }
        Write-Host "Staged libmpv into the shared runtime."
    }

    if ($DenoDir) {
        $source = Join-Path $DenoDir "deno.exe"
        if (-not (Test-Path $source)) {
            throw "deno.exe not found in -DenoDir '$DenoDir'."
        }
        $license = Join-Path $DenoDir "DENO-LICENSE.txt"
        if (-not (Test-Path $license)) {
            throw "DENO-LICENSE.txt not found in -DenoDir '$DenoDir' -- deno ships with its licence."
        }
        $target = Join-Path $RuntimeDist "tools\deno"
        New-Item -ItemType Directory -Force $target | Out-Null
        Copy-Item $source $target -Force
        Copy-Item $license $target -Force
        Write-Host "Staged deno into the shared runtime."
    }

    # The two AI engines, each with the licence files that must ride with it.
    # The named files are required, so a stage missing its licence (or, for
    # Copilot, a piece the SDK's completeness check needs) fails here rather
    # than shipping without it. Copilot is a whole bundle with subfolders
    # (Copy = "tree"): the target is emptied first so no file of an older
    # bundle -- the legacy single-file copilot.exe included -- survives beside
    # the new one. Codex is its named files only.
    $engines = @(
        @{ Dir = $CopilotDir; Name = "copilot"; Copy = "tree"; Files = @(
            "copilot.exe", "copilot-runtime.exe", "runtime.node",
            ".hostless-runtime-assets-v2", "COPILOT-CLI-LICENSE.txt") },
        @{ Dir = $CodexDir; Name = "codex"; Copy = "files"; Files = @(
            "codex-app-server.exe", "CODEX-LICENSE.txt", "CODEX-NOTICE.txt") }
    )
    foreach ($engine in $engines) {
        if (-not $engine.Dir) { continue }
        foreach ($file in $engine.Files) {
            if (-not (Test-Path -LiteralPath (Join-Path $engine.Dir $file))) {
                throw "$file not found in the $($engine.Name) directory '$($engine.Dir)' -- it ships with its licence."
            }
        }
        $target = Join-Path $RuntimeDist "tools\$($engine.Name)"
        if ($engine.Copy -eq "tree") {
            if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Recurse -Force }
            New-Item -ItemType Directory -Force $target | Out-Null
            # -Force so the dot-named marker is listed and copied too.
            Get-ChildItem -LiteralPath $engine.Dir -Force |
                ForEach-Object { Copy-Item -LiteralPath $_.FullName $target -Recurse -Force }
        } else {
            New-Item -ItemType Directory -Force $target | Out-Null
            foreach ($file in $engine.Files) {
                Copy-Item -LiteralPath (Join-Path $engine.Dir $file) $target -Force
            }
        }
        Write-Host "Staged $($engine.Name) into the shared runtime."
    }
}
