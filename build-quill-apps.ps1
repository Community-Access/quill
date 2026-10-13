<#
.SYNOPSIS
    Build QUILL apps for Windows, one after another, with logs and upload zips.

.DESCRIPTION
    Builds the apps you name, in the family's safe order (docs/building-windows-family.md):

      1. Checks the tools (Python 3.14, Inno Setup, Pandoc, the Podcast Index key).
      2. Rebuilds the shared QuillVille runtime (standalone/runtime/build_runtime.ps1),
         unless -SkipRuntime. Every sibling app packages that runtime, so it is
         rebuilt first.
      3. Runs the joint-release sibling version check once for every app being built
         (GATE-SIBVER, docs/release/RELEASE.md "A joint release of several apps").
      4. Builds each app's installer and portable zip with its own build script,
         passing the build number the source says (the app's _BUILD / APP_BUILD).
      5. Collects each app's fresh installer and portable zip into one upload folder,
         zips each app's pair, writes SHA256SUMS.txt, and zips everything together.

    Progress is plain text, one line per step ("Step 3 of 6: QUILL Cast"), with the
    build's own output shown as it runs and the time each step took, so it reads
    well with a screen reader. Everything is also written to log files.

    Builds are unsigned unless you pass -Sign. Nothing is published or uploaded.

.PARAMETER Apps
    Which apps to build. Any of:
      quill (QUILL for All), lite (or quilllite), inkwell, weather, beacon, social,
      converter, studio, cast, radio, transcribe
    or "all" for every one of them. Separate several with commas.

.PARAMETER SkipRuntime
    Do not rebuild the shared runtime (use the one already in standalone/runtime/dist).

.PARAMETER KeepGoing
    When one app fails, carry on with the rest instead of stopping.

.PARAMETER DryRun
    Print every command that would run, and run none of them.

.PARAMETER Python
    The Python 3.14 to build with. Default: the repo's .venv when it is 3.14,
    otherwise "py -3.14".

.PARAMETER Iscc
    Inno Setup's ISCC.exe. Default: the usual Inno Setup 7 (then 6) locations.

.PARAMETER Sign
    Sign the builds (needs signing credentials). Off by default.

.EXAMPLE
    .\build-quill-apps.ps1 lite,cast,radio,transcribe

.EXAMPLE
    .\build-quill-apps.ps1 all -KeepGoing

.EXAMPLE
    .\build-quill-apps.ps1 transcribe -DryRun
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0, Mandatory = $true)]
    [string[]]$Apps,
    [switch]$SkipRuntime,
    [switch]$KeepGoing,
    [switch]$DryRun,
    [string]$Python = "",
    [string]$Iscc = "",
    [switch]$Sign
)

$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot
Set-Location -LiteralPath $repo

# -- the apps ------------------------------------------------------------------

# In build order. "Name" is said in progress lines; "Id" is the release tools' id.
$catalog = [ordered]@{
    quill      = @{ Name = "QUILL for All";     Id = "quill" }
    quilllite  = @{ Name = "QUILL Lite";        Id = "quilllite" }
    inkwell    = @{ Name = "Quill Inkwell";     Id = "inkwell" }
    weather    = @{ Name = "Quill Weather";     Id = "weather" }
    beacon     = @{ Name = "Quill Beacon";      Id = "beacon" }
    social     = @{ Name = "Quill Social";      Id = "social" }
    converter  = @{ Name = "Quill Converter";   Id = "converter" }
    studio     = @{ Name = "Audio Studio";      Id = "studio" }
    cast       = @{ Name = "QUILL Cast";        Id = "cast" }
    radio      = @{ Name = "Quill Radio";       Id = "radio" }
    transcribe = @{ Name = "QUILL Transcribe";  Id = "transcribe" }
}
$aliases = @{ lite = "quilllite"; "quill-lite" = "quilllite"; podcasts = "cast"; all = "*" }

$wanted = New-Object System.Collections.Generic.List[string]
foreach ($raw in ($Apps -join ",").Split(",")) {
    $name = $raw.Trim().ToLowerInvariant()
    if (-not $name) { continue }
    if ($aliases.ContainsKey($name)) { $name = $aliases[$name] }
    if ($name -eq "*") { $catalog.Keys | ForEach-Object { if (-not $wanted.Contains($_)) { $wanted.Add($_) } }; continue }
    if (-not $catalog.Contains($name)) {
        throw "Unknown app '$raw'. Choose from: all, $((@($catalog.Keys) + 'lite') -join ', ')."
    }
    if (-not $wanted.Contains($name)) { $wanted.Add($name) }
}
# Always in the family's order, whatever order they were typed in.
$selected = @($catalog.Keys | Where-Object { $wanted.Contains($_) })
if (-not $selected) { throw "No apps chosen." }

# -- logs and output -----------------------------------------------------------

$stamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$runDir = Join-Path $repo "dist\release-builds\$stamp"
$logDir = Join-Path $runDir "logs"
$uploadDir = Join-Path $runDir "upload"
New-Item -ItemType Directory -Force -Path $logDir, $uploadDir | Out-Null
$mainLog = Join-Path $logDir "00-build-quill-apps.log"
$started = Get-Date

function Say([string]$text) {
    $line = "[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $text
    Write-Host $line
    Add-Content -LiteralPath $mainLog -Value $line -Encoding utf8
}

function Elapsed([datetime]$since) {
    $span = (Get-Date) - $since
    if ($span.TotalHours -ge 1) { return "{0}h {1}m {2}s" -f [int][math]::Floor($span.TotalHours), $span.Minutes, $span.Seconds }
    if ($span.TotalMinutes -ge 1) { return "{0}m {1}s" -f [int][math]::Floor($span.TotalMinutes), $span.Seconds }
    return "{0}s" -f [int]$span.TotalSeconds
}

# The PowerShell this script runs in, so each build runs in its own process
# and one that throws cannot take the others down.
$shell = (Get-Process -Id $PID).Path

# Run one command, show its output as it happens, keep it in a log. Returns the exit code.
function Invoke-Logged([string]$logName, [string]$exe, [string[]]$arguments) {
    $log = Join-Path $logDir $logName
    $shown = "$exe $($arguments -join ' ')"
    Add-Content -LiteralPath $log -Value "> $shown`r`n" -Encoding utf8
    if ($DryRun) {
        Say "  Would run: $shown"
        return 0
    }
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"  # a tool writing to stderr is not a failure; its exit code is
    try {
        & $exe @arguments 2>&1 | ForEach-Object {
            $text = "$_"
            Write-Host "    $text"
            Add-Content -LiteralPath $log -Value $text -Encoding utf8
        }
        $code = $LASTEXITCODE
    } catch {
        Add-Content -LiteralPath $log -Value "$_" -Encoding utf8
        Write-Host "    $_"
        $code = 1
    } finally {
        $ErrorActionPreference = $previous
    }
    if ($null -eq $code) { $code = 0 }
    Add-Content -LiteralPath $log -Value "`r`n< exit code $code" -Encoding utf8
    return [int]$code
}

function Invoke-BuildScript([string]$logName, [string]$script, [string[]]$arguments) {
    return Invoke-Logged $logName $shell (@("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $script) + $arguments)
}

# -- step plan -----------------------------------------------------------------

$steps = @("Checking tools")
if (-not $SkipRuntime) { $steps += "Shared runtime" }
$siblings = @($selected | Where-Object { $_ -ne "quill" })
if ($siblings) { $steps += "Sibling version check" }
$steps += @($selected | ForEach-Object { $catalog[$_].Name })
$steps += "Upload zips"
$stepCount = $steps.Count
$stepNumber = 0
function Step([string]$what) {
    $script:stepNumber++
    Say ""
    Say ("Step {0} of {1}: {2}" -f $script:stepNumber, $stepCount, $what)
}

Say "Building $($selected.Count) app(s): $(($selected | ForEach-Object { $catalog[$_].Name }) -join ', ')."
Say "Logs: $logDir"
if ($DryRun) { Say "Dry run: nothing will be built." }

# -- 1. tools ------------------------------------------------------------------

Step "Checking tools"
$pythonArgs = @()
if (-not $Python) {
    $venv = Join-Path $repo ".venv\Scripts\python.exe"
    if ((Test-Path -LiteralPath $venv) -and ((& $venv -c "import sys; print(sys.version_info[:2] == (3, 14))") -eq "True")) {
        $Python = $venv
    } else {
        $Python = (& py -3.14 -c "import sys; print(sys.executable)").Trim()
    }
}
if (-not (Test-Path -LiteralPath $Python)) { throw "Python not found: $Python" }
$pyVersion = (& $Python -c "import sys; print('%d.%d.%d' % sys.version_info[:3])").Trim()
Say "  Python $pyVersion at $Python"
if (-not $pyVersion.StartsWith("3.14.")) { throw "The family builds with Python 3.14; this is $pyVersion." }

if (-not $Iscc) {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 7\ISCC.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 7\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 7\ISCC.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe")
    )
    $Iscc = $candidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
}
if (-not $Iscc -or -not (Test-Path -LiteralPath $Iscc)) { throw "Inno Setup's ISCC.exe was not found. Install Inno Setup 7, or pass -Iscc." }
Say "  Inno Setup at $Iscc"

$pandoc = Get-Command pandoc -ErrorAction SilentlyContinue
if ($pandoc) { Say "  Pandoc at $($pandoc.Source)" } else { Say "  WARNING: Pandoc not found on PATH; the docs render step may fail." }

$keyFile = Join-Path $repo "quill\_podcast_index_key.py"
if (-not $SkipRuntime) {
    $hasKey = ($env:QUILL_PODCAST_INDEX_KEY -or $env:QUILL_PODCAST_INDEX_KEY_FILE) -or (Test-Path -LiteralPath $keyFile)
    if ($hasKey) { Say "  Podcast Index key: found" } else { throw "The shared runtime needs the Podcast Index key: set QUILL_PODCAST_INDEX_KEY and QUILL_PODCAST_INDEX_SECRET (or their _FILE forms), or keep quill\_podcast_index_key.py from an earlier build." }
}

$dirty = (& git status --porcelain) | Where-Object { $_ }
if ($dirty) { Say "  WARNING: the working tree has uncommitted changes; the builds include them." }
$commit = (& git rev-parse --short HEAD).Trim()
$branch = (& git rev-parse --abbrev-ref HEAD).Trim()
Say "  Source: $branch at $commit"
if ($Sign) { Say "  Signing: on" } else { Say "  Signing: off (unsigned builds)" }

# -- 2. shared runtime ---------------------------------------------------------

$results = New-Object System.Collections.Generic.List[object]
function Record([string]$what, [string]$status, [datetime]$since, [string]$log) {
    $results.Add([pscustomobject]@{ Step = $what; Status = $status; Time = (Elapsed $since); Log = $log })
}

if (-not $SkipRuntime) {
    Step "Shared runtime"
    $t = Get-Date
    $code = Invoke-BuildScript "01-runtime.log" (Join-Path $repo "standalone\runtime\build_runtime.ps1") @("-Python", $Python)
    if ($code -ne 0) {
        Record "Shared runtime" "FAILED" $t "01-runtime.log"
        Say "  FAILED after $(Elapsed $t). See logs\01-runtime.log. Every app needs the runtime, so stopping."
        $results | Format-Table -AutoSize | Out-String | Add-Content -LiteralPath $mainLog
        exit 1
    }
    Record "Shared runtime" "ok" $t "01-runtime.log"
    if (-not $DryRun) { Say "  Shared runtime built in $(Elapsed $t)." }
}

# -- 3. sibling version check --------------------------------------------------

if ($siblings) {
    Step "Sibling version check"
    $t = Get-Date
    $checkArgs = @("scripts\check_sibling_versions.py")
    foreach ($app in $siblings) { $checkArgs += @("--releasing", $catalog[$app].Id) }
    $code = Invoke-Logged "02-sibling-versions.log" $Python $checkArgs
    if ($code -ne 0) {
        Record "Sibling version check" "FAILED" $t "02-sibling-versions.log"
        Say "  FAILED. See logs\02-sibling-versions.log. A sibling would ship an unreleased version number."
        if (-not $KeepGoing) { exit 1 }
    } else {
        Record "Sibling version check" "ok" $t "02-sibling-versions.log"
        Say "  Passed for: $(($siblings | ForEach-Object { $catalog[$_].Id }) -join ', ')."
    }
}

# -- 4. the apps ---------------------------------------------------------------

# Which options each app's build script takes (they differ).
function Get-ScriptParams([string]$script) {
    $text = Get-Content -LiteralPath $script -Raw
    $names = @{}
    foreach ($match in [regex]::Matches($text, '\$(SkipSharedRuntime|SkipPublishedCheck|Build|Iscc|Sign)\b')) { $names[$match.Groups[1].Value] = $true }
    return $names
}

function Get-SourceBuild([string]$id) {
    $code = "import sys; sys.path.insert(0, 'scripts'); import release_build_number as r; print(r.source_build('$id'))"
    return [int]((& $Python -c $code).Trim())
}

$failed = 0
$index = 3
$artifacts = @{}
foreach ($app in $selected) {
    $info = $catalog[$app]
    Step $info.Name
    $t = Get-Date
    $logName = "{0:D2}-{1}.log" -f $index, $app
    $index++

    if ($app -eq "quill") {
        $outDir = Join-Path $repo "dist\windows"
        $code = Invoke-Logged $logName $Python @(
            "scripts\build_windows_distribution.py", "--bundle-python", "--compile-installer",
            "--iscc-path", $Iscc, "--output-dir", "dist/windows"
        )
        $found = @()
        if (-not $DryRun -and $code -eq 0) {
            $found += Get-ChildItem -Path (Join-Path $outDir "installer\Output") -Filter "*.exe" -File -ErrorAction SilentlyContinue | Where-Object LastWriteTime -ge $t
            $portable = Join-Path $outDir "portable"
            if (Test-Path -LiteralPath $portable) {
                $zip = Join-Path $runDir "Quill-for-All-Portable.zip"
                Compress-Archive -Path (Join-Path $portable "*") -DestinationPath $zip -Force
                $found += Get-Item -LiteralPath $zip
            }
        }
    } else {
        $script = Join-Path $repo "standalone\$app\scripts\build_release.ps1"
        $params = Get-ScriptParams $script
        $buildArgs = @("-Python", $Python)
        if ($params.Iscc) { $buildArgs += @("-Iscc", $Iscc) }
        if ($params.SkipSharedRuntime) { $buildArgs += "-SkipSharedRuntime" }
        if ($params.SkipPublishedCheck) { $buildArgs += "-SkipPublishedCheck" }
        if ($params.Build) {
            $build = Get-SourceBuild $info.Id
            $buildArgs += @("-Build", "$build")
            Say "  Build number from the source: $build"
        }
        if ($Sign -and $params.Sign) { $buildArgs += "-Sign" }
        $code = Invoke-BuildScript $logName $script $buildArgs
        $found = @()
        if (-not $DryRun -and $code -eq 0) {
            $found = @(Get-ChildItem -LiteralPath (Join-Path $repo "standalone\$app\dist") -File -ErrorAction SilentlyContinue |
                Where-Object { $_.Extension -in ".exe", ".zip" -and $_.LastWriteTime -ge $t })
        }
    }

    if ($code -ne 0) {
        $failed++
        Record $info.Name "FAILED" $t $logName
        Say "  $($info.Name) FAILED after $(Elapsed $t). See logs\$logName."
        if (-not $KeepGoing) { break }
        continue
    }
    if (-not $DryRun -and -not $found) {
        $failed++
        Record $info.Name "NO FILES" $t $logName
        Say "  $($info.Name) finished but no new installer or zip was found. See logs\$logName."
        if (-not $KeepGoing) { break }
        continue
    }
    $artifacts[$app] = $found
    Record $info.Name "ok" $t $logName
    if ($DryRun) { continue }
    Say "  $($info.Name) built in $(Elapsed $t):"
    foreach ($file in $found) { Say ("    {0} ({1:N1} MB)" -f $file.Name, ($file.Length / 1MB)) }
}

# -- 5. upload zips ------------------------------------------------------------

Step "Upload zips"
if ($DryRun) {
    Say "  Would copy each app's installer and portable zip to $uploadDir, zip each app, and write SHA256SUMS.txt."
} elseif ($artifacts.Count -eq 0) {
    Say "  Nothing was built, so there is nothing to zip."
} else {
    $sums = New-Object System.Collections.Generic.List[string]
    foreach ($app in $selected) {
        if (-not $artifacts.ContainsKey($app)) { continue }
        $appDir = Join-Path $uploadDir $app
        New-Item -ItemType Directory -Force -Path $appDir | Out-Null
        foreach ($file in $artifacts[$app]) {
            Copy-Item -LiteralPath $file.FullName -Destination $appDir -Force
            $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            $sums.Add("$hash  $app/$($file.Name)")
        }
        $appZip = Join-Path $uploadDir "$app-$stamp.zip"
        Compress-Archive -Path (Join-Path $appDir "*") -DestinationPath $appZip -Force
        Say ("  {0}: {1} ({2:N1} MB)" -f $catalog[$app].Name, (Split-Path $appZip -Leaf), ((Get-Item $appZip).Length / 1MB))
    }
    $sumsFile = Join-Path $uploadDir "SHA256SUMS.txt"
    $sums | Set-Content -LiteralPath $sumsFile -Encoding ascii
    $everything = Join-Path $runDir "quill-apps-$stamp.zip"
    Compress-Archive -Path (Join-Path $uploadDir "*") -DestinationPath $everything -Force
    Say ("  Everything in one zip: {0} ({1:N1} MB)" -f $everything, ((Get-Item $everything).Length / 1MB))
    Say "  Checksums: $sumsFile"
}

# -- summary -------------------------------------------------------------------

$summary = Join-Path $runDir "summary.txt"
$table = $results | Format-Table Step, Status, Time, Log -AutoSize | Out-String
@(
    "QUILL app builds, $stamp",
    "Source: $branch at $commit$(if ($dirty) { ' (with uncommitted changes)' })",
    "Python $pyVersion; signing $(if ($Sign) { 'on' } else { 'off' })",
    $table
) | Set-Content -LiteralPath $summary -Encoding utf8

Say ""
$ok = @($results | Where-Object Status -eq "ok").Count
Say "Finished in $(Elapsed $started). $ok step(s) succeeded, $failed app(s) failed."
Say "Summary: $summary"
Say "Upload folder: $uploadDir"
if ($failed) { exit 1 }
exit 0
