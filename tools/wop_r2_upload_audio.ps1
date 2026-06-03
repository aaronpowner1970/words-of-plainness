<#
.SYNOPSIS
    WoP R2 Audio Upload — narrations, podcasts, spoken word, music.

.DESCRIPTION
    Uploads one or more MP3 files to Cloudflare R2 under the wop-media/web/
    prefix, which is the canonical location for all audio served by the
    Eleventy site and the music player.

    R2 path structure (permanent standard):
        wop-media/web/<filename>.mp3

    CDN base: https://media.wordsofplainness.org/web/

    Content-type is set to audio/mpeg on every upload so browsers stream
    correctly.

.PARAMETER Files
    One or more local MP3 file paths. Accepts pipeline input.

.PARAMETER DryRun
    List files that would be uploaded without actually uploading.

.EXAMPLE
    # Upload a single podcast replacement
    .\tools\wop_r2_upload_audio.ps1 `
        -Files "C:\Users\aaron\Documents\working-folder\podcast-normalize\PO_04_01_Spiritual_Knowledge.mp3"

.EXAMPLE
    # Batch upload multiple files
    .\tools\wop_r2_upload_audio.ps1 `
        -Files "C:\path\to\PO_04_01_Spiritual_Knowledge.mp3", `
               "C:\path\to\NR_04_01_Spiritual_Knowledge.mp3"

.EXAMPLE
    # Dry run
    .\tools\wop_r2_upload_audio.ps1 -Files "C:\path\to\file.mp3" -DryRun
#>

param(
    [Parameter(Mandatory, ValueFromPipeline=$true)]
    [string[]]$Files,

    [switch]$DryRun
)

begin {
    $ErrorActionPreference = 'Stop'

    # --- Locate repo root and load config ---
    $scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
    $configPath = Join-Path $scriptDir 'wop_r2_config.json'

    if (-not (Test-Path $configPath)) {
        Write-Error "Config not found: $configPath"
        exit 1
    }

    $cfg       = Get-Content $configPath -Raw | ConvertFrom-Json
    $accountId = $cfg.account_id
    $accessKey = $cfg.access_key_id
    $secretKey = $cfg.secret_access_key
    $bucket    = $cfg.default_bucket        # wop-media
    $cdnHost   = $cfg.cdn_hostname          # media.wordsofplainness.org
    $prefix    = 'web'

    # --- Set credentials for wrangler ---
    $env:CLOUDFLARE_ACCOUNT_ID = $accountId
    $env:AWS_ACCESS_KEY_ID     = $accessKey
    $env:AWS_SECRET_ACCESS_KEY = $secretKey

    $cdnBase   = "https://$cdnHost/$prefix/"

    Write-Host ""
    Write-Host "WoP R2 Audio Upload" -ForegroundColor White
    Write-Host "Bucket  : $bucket" -ForegroundColor Gray
    Write-Host "R2 path : $prefix/" -ForegroundColor Gray
    Write-Host "CDN base: $cdnBase" -ForegroundColor Gray
    if ($DryRun) {
        Write-Host "MODE    : DRY RUN — no files will be uploaded" -ForegroundColor Yellow
    }
    Write-Host ("=" * 70) -ForegroundColor DarkGray
    Write-Host ""

    $passCount = 0
    $failCount = 0
    $uploaded  = @()
}

process {
    foreach ($localPath in $Files) {
        if (-not (Test-Path -LiteralPath $localPath)) {
            Write-Host "  MISSING: $localPath" -ForegroundColor Red
            $failCount++
            continue
        }

        $fileItem = Get-Item -LiteralPath $localPath
        $r2Key    = "$prefix/$($fileItem.Name)"
        $cdnUrl   = "$cdnBase$($fileItem.Name)"
        $sizeMb   = [math]::Round($fileItem.Length / 1MB, 2)

        Write-Host ("  {0}  ({1} MB)" -f $r2Key, $sizeMb) -ForegroundColor Cyan -NoNewline

        if ($DryRun) {
            Write-Host "  [dry-run]" -ForegroundColor Yellow
            continue
        }

        try {
            $result = npx wrangler r2 object put "$bucket/$r2Key" `
                --file $fileItem.FullName `
                --content-type "audio/mpeg" `
                --remote 2>&1

            if ($LASTEXITCODE -eq 0) {
                Write-Host "  ok" -ForegroundColor Green
                $passCount++
                $uploaded += $cdnUrl
            } else {
                Write-Host "  FAILED" -ForegroundColor Red
                Write-Host "    $result" -ForegroundColor Red
                $failCount++
            }
        } catch {
            Write-Host "  ERROR: $_" -ForegroundColor Red
            $failCount++
        }
    }
}

end {
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor DarkGray

    if ($DryRun) {
        Write-Host "  DRY RUN complete." -ForegroundColor Yellow
    } elseif ($failCount -eq 0) {
        Write-Host "  ALL CLEAR: $passCount uploaded successfully" -ForegroundColor Green
        Write-Host ""
        Write-Host "  CDN URLs:" -ForegroundColor White
        foreach ($u in $uploaded) { Write-Host "    $u" -ForegroundColor Gray }
        Write-Host ""
        Write-Host "  NOTE: Cloudflare edge cache may still serve the previous" -ForegroundColor DarkYellow
        Write-Host "        object. Purge the specific URL in the Cloudflare" -ForegroundColor DarkYellow
        Write-Host "        dashboard (Caching > Configuration > Purge Cache >" -ForegroundColor DarkYellow
        Write-Host "        Custom Purge) or append a cache-buster query" -ForegroundColor DarkYellow
        Write-Host "        string (?v=timestamp) when verifying." -ForegroundColor DarkYellow
    } else {
        Write-Host "  ATTENTION: $failCount failed, $passCount succeeded" -ForegroundColor Red
    }

    Write-Host ""
}
