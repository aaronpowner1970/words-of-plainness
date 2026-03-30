# ============================================================
# WoP R2 — Single PDF Upload
# Target: docs/Ch09_Suite_Listener_Notes.pdf
# CDN URL: https://media.wordsofplainness.org/docs/Ch09_Suite_Listener_Notes.pdf
# ============================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$configPath = "tools\wop_r2_config.json"
$config     = Get-Content $configPath | ConvertFrom-Json

$env:CLOUDFLARE_ACCOUNT_ID = $config.account_id
$env:AWS_ACCESS_KEY_ID     = $config.access_key_id
$env:AWS_SECRET_ACCESS_KEY = $config.secret_access_key

$bucket    = $config.default_bucket   # wop-media
$r2Key     = "docs/Ch09_Suite_Listener_Notes.pdf"
$localPath = $args[0]

if (-not $localPath) {
    Write-Error "Usage: .\wop_r2_upload_pdf.ps1 <path-to-pdf>"
    Write-Host  "Example: .\wop_r2_upload_pdf.ps1 C:\Users\aaron\Downloads\Ch09_Suite_Listener_Notes.pdf"
    exit 1
}

if (-not (Test-Path $localPath)) {
    Write-Error "File not found: $localPath"
    exit 1
}

Write-Host ""
Write-Host "  Uploading: $r2Key"
Write-Host "  From     : $localPath"
Write-Host ""

$result = npx wrangler r2 object put "$bucket/$r2Key" `
    --file $localPath `
    --content-type "application/pdf" `
    --remote 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK — uploaded successfully." -ForegroundColor Green
    Write-Host ""
    Write-Host "  CDN URL: https://media.wordsofplainness.org/docs/Ch09_Suite_Listener_Notes.pdf"
} else {
    Write-Host "  FAILED" -ForegroundColor Red
    Write-Host $result
    exit 1
}
