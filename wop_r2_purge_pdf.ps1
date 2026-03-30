# ============================================================
# WoP R2 — Purge PDF from Cloudflare CDN cache
# Run this after uploading a new PDF to R2
# ============================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$config    = Get-Content "tools\wop_r2_config.json" | ConvertFrom-Json
$accountId = $config.account_id

# ── Step 1: Get Zone ID for wordsofplainness.org ───────────────────────────
# We need a Cloudflare API token with Cache Purge + Zone Read permissions
# Get one at: https://dash.cloudflare.com/profile/api-tokens
$apiToken = Read-Host "Enter your Cloudflare API token (needs Zone:Read + Cache Purge)"

$headers = @{
    "Authorization" = "Bearer $apiToken"
    "Content-Type"  = "application/json"
}

Write-Host ""
Write-Host "  Looking up Zone ID for wordsofplainness.org ..."
$zoneResp = Invoke-RestMethod `
    -Uri "https://api.cloudflare.com/client/v4/zones?name=wordsofplainness.org&account.id=$accountId" `
    -Method Get `
    -Headers $headers

if (-not $zoneResp.success -or $zoneResp.result.Count -eq 0) {
    Write-Error "Could not find zone for wordsofplainness.org. Check token permissions."
    exit 1
}

$zoneId = $zoneResp.result[0].id
Write-Host "  Zone ID: $zoneId" -ForegroundColor Green

# ── Step 2: Purge the PDF URL ──────────────────────────────────────────────
$purgeUrl = "https://media.wordsofplainness.org/docs/Ch09_Suite_Listener_Notes.pdf"
Write-Host ""
Write-Host "  Purging: $purgeUrl ..."

$purgeBody = @{ files = @($purgeUrl) } | ConvertTo-Json
$purgeResp = Invoke-RestMethod `
    -Uri "https://api.cloudflare.com/client/v4/zones/$zoneId/purge_cache" `
    -Method Post `
    -Headers $headers `
    -Body $purgeBody

if ($purgeResp.success) {
    Write-Host "  Purge successful." -ForegroundColor Green
    Write-Host ""
    Write-Host "  Wait 10-15 seconds, then reload:"
    Write-Host "  $purgeUrl"
} else {
    Write-Host "  Purge failed:" -ForegroundColor Red
    Write-Host ($purgeResp | ConvertTo-Json)
    exit 1
}
