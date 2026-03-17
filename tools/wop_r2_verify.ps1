<#
.SYNOPSIS
    WoP R2 CDN Verification - pre-flight spot-check for media.wordsofplainness.org
.DESCRIPTION
    Step 6 of the deployment pre-flight checklist.
    Confirms audio files are live and serving correctly from the CDN.
.PARAMETER Files
    Optional array of specific filenames to verify. If omitted, runs a
    spot check with one representative file per prefix type (NR, PO, SW, AM, AN, SY, chapter music).
.EXAMPLE
    .\tools\wop_r2_verify.ps1
    # Default spot check - one file per prefix type
.EXAMPLE
    .\tools\wop_r2_verify.ps1 -Files @("NR_07_01_Prophecies_Birth_and_Youth.mp3","PO_07_01_Prophecies_Birth_and_Youth.mp3")
    # Targeted verification of specific files
#>
param(
    [string[]]$Files
)

$ErrorActionPreference = 'Stop'

# --- Locate repo root and config ---
$scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot   = Split-Path -Parent $scriptDir
$configPath = Join-Path $scriptDir 'wop_r2_config.json'

$cdnHostname = 'media.wordsofplainness.org'
if (Test-Path $configPath) {
    $cfg = Get-Content $configPath -Raw | ConvertFrom-Json
    if ($cfg.cdn_hostname) { $cdnHostname = $cfg.cdn_hostname }
}

$cdnBase = "https://$cdnHostname/web/"

# --- Build file list ---
if (-not $Files -or $Files.Count -eq 0) {
    Write-Host "Mode: DEFAULT spot check (one file per prefix type)" -ForegroundColor Cyan
    $spotFiles = @()
    $prefixHit = @{ NR = $false; PO = $false; SW = $false; AM = $false; AN = $false; SY = $false; CH = $false }

    # 1. ministryMusic.json -> AM, AN, SY
    $musicPath = Join-Path $repoRoot 'src\_data\ministryMusic.json'
    if (Test-Path $musicPath) {
        $music = Get-Content $musicPath -Raw | ConvertFrom-Json

        if ($music.ambient -and $music.ambient.Count -gt 0) {
            $spotFiles += $music.ambient[0].file
            $prefixHit['AM'] = $true
        }
        foreach ($item in $music.collection) {
            if (-not $prefixHit['AN'] -and $item.file -match '^AN_') {
                $spotFiles += $item.file; $prefixHit['AN'] = $true
            }
            if (-not $prefixHit['SY'] -and $item.file -match '^SY_') {
                $spotFiles += $item.file; $prefixHit['SY'] = $true
            }
        }
    }

    # 2. Chapter frontmatter -> NR, PO, chapter music
    $chapDir = Join-Path $repoRoot 'src\chapters'
    if (Test-Path $chapDir) {
        $mdFiles = Get-ChildItem -Path $chapDir -Filter '*.md' |
                   Where-Object { $_.Name -ne '_template.md' } |
                   Sort-Object Name
        foreach ($md in $mdFiles) {
            $text = [System.IO.File]::ReadAllText($md.FullName)
            # Match any YAML value containing an .mp3 filename (file:, narration:, overview:, etc.)
            $fileRefs = [regex]::Matches($text, '(?:file|narration|overview):\s*"?([A-Za-z0-9_.\-]+\.mp3)"?')
            foreach ($ref in $fileRefs) {
                $fname = $ref.Groups[1].Value
                if (-not $prefixHit['NR'] -and $fname -match '^NR_') {
                    $spotFiles += $fname; $prefixHit['NR'] = $true
                }
                if (-not $prefixHit['PO'] -and $fname -match '^PO_') {
                    $spotFiles += $fname; $prefixHit['PO'] = $true
                }
                if (-not $prefixHit['CH'] -and $fname -match '^\d') {
                    $spotFiles += $fname; $prefixHit['CH'] = $true
                }
            }
            if ($prefixHit['NR'] -and $prefixHit['PO'] -and $prefixHit['CH']) { break }
        }
    }

    # 3. Concert data -> SW
    $concertDir = Join-Path $repoRoot 'src\_data\concerts'
    if (Test-Path $concertDir) {
        $jsonFiles = Get-ChildItem -Path $concertDir -Filter '*.json'
        foreach ($jf in $jsonFiles) {
            $jText = [System.IO.File]::ReadAllText($jf.FullName)
            $swRefs = [regex]::Matches($jText, '(SW_[A-Za-z0-9_.\-]+\.mp3)')
            if ($swRefs.Count -gt 0) {
                $spotFiles += $swRefs[0].Groups[1].Value
                $prefixHit['SW'] = $true
                break
            }
        }
    }

    # Fallback: scan ch06 full for inline SW_ ref
    if (-not $prefixHit['SW']) {
        $ch06 = Join-Path $repoRoot 'src\chapters\06-embrace-the-savior-full.md'
        if (Test-Path $ch06) {
            $ch06Text = [System.IO.File]::ReadAllText($ch06)
            $swInline = [regex]::Match($ch06Text, '(SW_[A-Za-z0-9_.\-]+\.mp3)')
            if ($swInline.Success) {
                $spotFiles += $swInline.Groups[1].Value
                $prefixHit['SW'] = $true
            }
        }
    }

    $Files = $spotFiles

    # Report any missing prefix types
    foreach ($key in $prefixHit.Keys) {
        if (-not $prefixHit[$key]) {
            Write-Host "  NOTE: No $key file found in repo sources" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "Mode: TARGETED verification ($($Files.Count) file(s))" -ForegroundColor Cyan
}

if ($Files.Count -eq 0) {
    Write-Host "No files to verify." -ForegroundColor Yellow
    exit 1
}

# --- Verify each file ---
Write-Host ""
Write-Host "WoP R2 CDN Verification" -ForegroundColor White
Write-Host "CDN: $cdnBase" -ForegroundColor Gray
Write-Host ("=" * 70)

$passCount = 0
$failCount = 0
$results   = @()

foreach ($file in $Files) {
    $url = "$cdnBase$file"
    try {
        $response = Invoke-WebRequest -Uri $url -Method Head -UseBasicParsing
        $status      = $response.StatusCode
        $contentType = $response.Headers['Content-Type']

        if ($status -eq 200 -and $contentType -match 'audio/mpeg') {
            Write-Host "  PASS  $file" -ForegroundColor Green
            $passCount++
        } else {
            $reason = "[$status, Content-Type: $contentType]"
            Write-Host "  FAIL  $file  $reason" -ForegroundColor Red
            $failCount++
        }
    } catch {
        $errMsg = $_.Exception.Message
        # Extract HTTP status if available
        if ($_.Exception.Response) {
            $code = [int]$_.Exception.Response.StatusCode
            $desc = $_.Exception.Response.StatusDescription
            $errMsg = "$code $desc"
        }
        Write-Host "  FAIL  $file  [$errMsg]" -ForegroundColor Red
        $failCount++
    }
}

$total = $passCount + $failCount
Write-Host ("=" * 70)

if ($failCount -eq 0) {
    Write-Host "  ALL CLEAR: $passCount/$total passed" -ForegroundColor Green
} else {
    Write-Host "  ATTENTION: $failCount file(s) failed ($passCount/$total passed)" -ForegroundColor Red
}

Write-Host ""
