# wop_r2_upload_file.ps1
# Upload a single file to Cloudflare R2 wop-media/web/
# Reads credentials from tools\wop_r2_config.json automatically.
#
# Usage (from repo root):
#   .\wop_r2_upload_file.ps1 -File "C:\path\to\file.mp3"
#
# The file is uploaded to wop-media/web/<filename> and served at:
#   https://media.wordsofplainness.org/web/<filename>

param(
    [Parameter(Mandatory=$true)]
    [string]$File
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Load credentials from config
$config = Get-Content "tools\wop_r2_config.json" | ConvertFrom-Json
$env:CLOUDFLARE_ACCOUNT_ID = $config.account_id
$env:AWS_ACCESS_KEY_ID     = $config.access_key_id
$env:AWS_SECRET_ACCESS_KEY = $config.secret_access_key

$filename = Split-Path $File -Leaf
$r2Key    = "wop-media/web/$filename"
$cdnUrl   = "https://media.wordsofplainness.org/web/$filename"

Write-Host ""
Write-Host "Uploading: $filename"
Write-Host "  Source : $File"
Write-Host "  R2 key : $r2Key"
Write-Host "  CDN URL: $cdnUrl"
Write-Host ""

npx wrangler r2 object put $r2Key --file $File --content-type "audio/mpeg" --remote

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Upload complete." -ForegroundColor Green
    Write-Host "Verify: $cdnUrl"
} else {
    Write-Host ""
    Write-Host "Upload FAILED. Check wrangler output above." -ForegroundColor Red
    exit 1
}
