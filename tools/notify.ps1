# Words of Plainness — Post Distribution Notifier
# Usage: .\tools\notify.ps1
# Fires all configured notification channels (Discord, X, Facebook)
#
# IMPORTANT: Replace PASTE_YOUR_NOTIFY_SECRET_HERE with your actual NOTIFY_SECRET.
# Do NOT commit this file to git with the real secret in place.

$secret = "PASTE_YOUR_NOTIFY_SECRET_HERE"
$url = "https://www.wordsofplainness.org/api/notify-all"

Write-Host "Firing notification pipeline..." -ForegroundColor Yellow

$response = Invoke-RestMethod -Uri $url -Method POST -Headers @{
    "Authorization" = "Bearer $secret"
} -ContentType "application/json"

Write-Host "`nPost: $($response.post)" -ForegroundColor Cyan
Write-Host "URL:  $($response.url)`n" -ForegroundColor Cyan

foreach ($platform in @("discord", "x", "facebook")) {
    $result = $response.results.$platform
    $color = switch ($result.status) {
        "sent"    { "Green" }
        "skipped" { "DarkYellow" }
        "error"   { "Red" }
    }
    Write-Host "  $($platform.ToUpper().PadRight(10)) $($result.status)  $($result.detail)" -ForegroundColor $color
}

Write-Host "`nDone." -ForegroundColor Green
