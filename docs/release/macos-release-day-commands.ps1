# QUILL macOS signed/notarized release day commands
# Usage:
#   1) Fill in the placeholder variables in this file.
#   2) Run line by line in PowerShell, or execute this script directly.
# Notes:
#   - This script sets GitHub secrets and triggers workflow runs.
#   - Do not commit real secret values.

$ErrorActionPreference = "Stop"

# --------
# Settings
# --------
$Owner = "Community-Access"
$Repo = "quill"
$RepoRoot = "S:\quill"
$EnvironmentName = "macos-release"
$BranchName = "feature/table-studio"
$TagVersion = "vX.Y.Z"

# File paths to your Apple credential files.
$P12Path = "C:\path\to\DeveloperID.p12"
$ApiKeyP8Path = "C:\path\to\AuthKey_ABC123XYZ.p8"

# Optional: set to $true when you want to create and push the version tag.
$DoTagPush = $false

Write-Host "==> Repo preflight"
Set-Location $RepoRoot

gh auth status
gh repo set-default "$Owner/$Repo"

Write-Host "==> Ensure GitHub Actions environment exists"
gh api --method PUT "repos/$Owner/$Repo/environments/$EnvironmentName"

Write-Host "==> Upload file-based secrets"
[Convert]::ToBase64String([IO.File]::ReadAllBytes($P12Path)) | gh secret set -e $EnvironmentName BUILD_CERTIFICATE_BASE64
[Convert]::ToBase64String([IO.File]::ReadAllBytes($ApiKeyP8Path)) | gh secret set -e $EnvironmentName APPLE_API_KEY_B64

Write-Host "==> Set prompted text secrets"
Write-Host "When prompted, paste each value from your secure vault."
gh secret set -e $EnvironmentName P12_PASSWORD
gh secret set -e $EnvironmentName KEYCHAIN_PASSWORD
gh secret set -e $EnvironmentName MACOS_CODESIGN_IDENTITY
gh secret set -e $EnvironmentName APPLE_API_KEY_ID
gh secret set -e $EnvironmentName APPLE_API_ISSUER
gh secret set -e $EnvironmentName APPLE_TEAM_ID

Write-Host "==> Confirm environment secrets"
gh secret list -e $EnvironmentName

Write-Host "==> Branch dry run"
gh workflow run macos-release.yml --ref $BranchName
gh run list --workflow macos-release.yml --limit 5
gh run watch

Write-Host "==> Optional: open run details"
gh run view --web

if ($DoTagPush) {
    Write-Host "==> Tag and push release"
    git tag -s $TagVersion -m "QUILL $TagVersion"
    git push origin $TagVersion

    Write-Host "==> Watch tag-triggered macOS workflow"
    gh run list --workflow macos-release.yml --limit 5
    gh run watch
}

Write-Host "Done. Verify Quill.dmg artifact and clean-machine macOS install before external beta publish."
