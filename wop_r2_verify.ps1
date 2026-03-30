# ============================================================
# WoP R2 CDN Verification Script — Runbook Prompt 4
# Spot-checks CDN delivery of uploaded MP3 files
# Run AFTER wop_r2_upload.ps1 completes with 0 failures
# ============================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$config      = Get-Content "tools\wop_r2_config.json" | ConvertFrom-Json
$cdnHostname = $config.cdn_hostname    # media.wordsofplainness.org
$prefix      = $config.default_prefix  # web

# Spot-check these files — one from each chapter/prefix type
$spotCheck = @(
    "01_01_Introduction_to_Plainness_Sacred_Americana.mp3",
    "03_02_Two_Halves_of_a_Whole_Americana_Folk.mp3",
    "05_06_The_Souls_Sincere_Desire_Broadway_Ballad.mp3",
    "06_09_I_Have_Tasted_the_Light_Indie_Folk.mp3",
    "AM_04_Ambient_Reading_Atmosphere_Meditation.mp3",
    "AN_01_The_Marks_of_Your_Worth_Sacred_Americana.mp3",
    "NR_03_01_Academic_Knowledge.mp3",
    "PO_05_01_Sincere_Prayer.mp3",
    "SW_06_01_I_Have_Tasted_the_Light.mp3",
    "SY_01_Words_of_Plainness_Mini_Symphony_Instrumental.mp3"
)

Write-Host ""
Write-Host "============================================================"
Write-Host " WoP R2 CDN Verification — Spot Check (10 files)"
Write-Host " CDN base: https://$cdnHostname/$prefix/"
Write-Host "============================================================"
Write-Host ""

$passCount = 0
$failCount = 0
$failures  = @()

foreach ($filename in $spotCheck) {
    $url = "https://$cdnHostname/$prefix/$filename"
    Write-Host -NoNewline "  $filename ... "

    try {
        # HEAD request — check status code and Content-Type only
        $response = Invoke-WebRequest -Uri $url -Method Head -TimeoutSec 15

        $status      = $response.StatusCode
        $contentType = $response.Headers["Content-Type"]

        if ($status -eq 200 -and $contentType -like "*audio*") {
            Write-Host "OK (HTTP $status, $contentType)" -ForegroundColor Green
            $passCount++
        } elseif ($status -eq 200) {
            Write-Host "WARN — HTTP 200 but Content-Type: $contentType" -ForegroundColor Yellow
            $passCount++  # Still usable, but worth noting
        } else {
            Write-Host "FAIL — HTTP $status" -ForegroundColor Red
            $failCount++
            $failures += "$filename (HTTP $status)"
        }
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Write-Host "FAIL — $($_.Exception.Message)" -ForegroundColor Red
        $failCount++
        $failures += "$filename ($($_.Exception.Message))"
    }
}

Write-Host ""
Write-Host "============================================================"
Write-Host " Verification Summary"
Write-Host "============================================================"
Write-Host " Passed : $passCount / $($spotCheck.Count)"
Write-Host " Failed : $failCount / $($spotCheck.Count)"

if ($failures.Count -gt 0) {
    Write-Host ""
    Write-Host " Failures:" -ForegroundColor Red
    foreach ($f in $failures) {
        Write-Host "   - $f" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host " DO NOT switch audioBaseUrl until all spot checks pass."
    exit 1
}

Write-Host ""
Write-Host " All spot checks passed." -ForegroundColor Green
Write-Host ""
Write-Host " READY to switch audioBaseUrl in .eleventy.js"
Write-Host " New value: https://$cdnHostname/$prefix"
Write-Host "============================================================"
Write-Host ""
Write-Host " Eleventy change:"
Write-Host "   Find  : audioBaseUrl: '/assets/audio'"
Write-Host "   Replace: audioBaseUrl: 'https://$cdnHostname/$prefix'"
Write-Host ""
Write-Host " After editing .eleventy.js:"
Write-Host "   git add .eleventy.js"
Write-Host "   git commit -m 'feat: switch audio delivery to Cloudflare R2 CDN'"
Write-Host "   git push"
Write-Host "   (Vercel will auto-deploy)"
Write-Host "============================================================"
