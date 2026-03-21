<#
.SYNOPSIS
    WoP R2 Image Upload — slides and visual summaries
.DESCRIPTION
    Uploads PNG images (study slides and infographics) to Cloudflare R2
    under the wop-media/images/ prefix, organized by chapter subfolder.

    R2 path structure (permanent standard):
        wop-media/images/chapter-##/slide-01.png   (slides)
        wop-media/images/chapter-##/chapter-##-infographic.png  (visual summary)

    CDN base: https://media.wordsofplainness.org/images/

.PARAMETER ChapterFolder
    The chapter subfolder name, e.g. "chapter-08". Must match the
    slides.path value in the chapter's frontmatter (without trailing slash).

.PARAMETER SourceFolder
    Local folder containing the PNG files to upload.
    Defaults to: working-folder\ch##-slides  (inferred from ChapterFolder)

.PARAMETER Infographic
    Optional path to a single infographic PNG to upload alongside slides.
    If omitted, only slide-##.png files are uploaded.

.PARAMETER DryRun
    List files that would be uploaded without actually uploading.

.EXAMPLE
    # Upload Ch 8 slides + infographic
    .\tools\wop_r2_upload_images.ps1 `
        -ChapterFolder "chapter-08" `
        -SourceFolder "C:\Users\aaron\Documents\working-folder\ch08-slides" `
        -Infographic "C:\Users\aaron\Documents\working-folder\ch08_visual_summary.png"

.EXAMPLE
    # Dry run
    .\tools\wop_r2_upload_images.ps1 `
        -ChapterFolder "chapter-08" `
        -SourceFolder "C:\Users\aaron\Documents\working-folder\ch08-slides" `
        -Infographic "C:\Users\aaron\Documents\working-folder\ch08_visual_summary.png" `
        -DryRun
#>

param(
    [Parameter(Mandatory)]
    [string]$ChapterFolder,

    [string]$SourceFolder = "",

    [string]$Infographic = "",

    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

# --- Locate repo root and load config ---
$scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot   = Split-Path -Parent $scriptDir
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

$r2Prefix  = "images/$ChapterFolder"
$cdnBase   = "https://$cdnHost/images/$ChapterFolder/"

# --- Set credentials for wrangler ---
$env:CLOUDFLARE_ACCOUNT_ID = $accountId
$env:AWS_ACCESS_KEY_ID     = $accessKey
$env:AWS_SECRET_ACCESS_KEY = $secretKey

# --- Resolve source folder ---
if (-not $SourceFolder) {
    # Infer: working-folder/ch##-slides  (e.g. chapter-08 -> ch08-slides)
    $num = ($ChapterFolder -replace '^chapter-', '')
    $SourceFolder = Join-Path (Split-Path -Parent $repoRoot) "working-folder\ch$num-slides"
}

if (-not (Test-Path $SourceFolder)) {
    Write-Error "Source folder not found: $SourceFolder"
    exit 1
}

# --- Build upload list ---
# Slides: slide-01.png through slide-NN.png
$slides = Get-ChildItem -Path $SourceFolder -Filter "slide-*.png" |
          Sort-Object Name

$uploadList = @()

foreach ($slide in $slides) {
    $uploadList += [PSCustomObject]@{
        LocalPath = $slide.FullName
        R2Key     = "$r2Prefix/$($slide.Name)"
        CDNUrl    = "$cdnBase$($slide.Name)"
    }
}

# Infographic (renamed on upload to match frontmatter convention)
if ($Infographic) {
    if (-not (Test-Path $Infographic)) {
        Write-Error "Infographic not found: $Infographic"
        exit 1
    }
    $infName = "$ChapterFolder-infographic.png"
    $uploadList += [PSCustomObject]@{
        LocalPath = $Infographic
        R2Key     = "$r2Prefix/$infName"
        CDNUrl    = "$cdnBase$infName"
    }
}

if ($uploadList.Count -eq 0) {
    Write-Host "No files found to upload in: $SourceFolder" -ForegroundColor Yellow
    exit 1
}

# --- Summary ---
Write-Host ""
Write-Host "WoP R2 Image Upload" -ForegroundColor White
Write-Host "Bucket  : $bucket" -ForegroundColor Gray
Write-Host "R2 path : $r2Prefix/" -ForegroundColor Gray
Write-Host "CDN base: $cdnBase" -ForegroundColor Gray
if ($DryRun) {
    Write-Host "MODE    : DRY RUN — no files will be uploaded" -ForegroundColor Yellow
}
Write-Host ("=" * 70)
Write-Host ""

$passCount = 0
$failCount = 0

foreach ($item in $uploadList) {
    Write-Host "  $($item.R2Key)" -ForegroundColor Cyan -NoNewline

    if ($DryRun) {
        Write-Host "  [dry-run]" -ForegroundColor Yellow
        continue
    }

    try {
        $result = npx wrangler r2 object put "$bucket/$($item.R2Key)" `
            --file $item.LocalPath `
            --content-type "image/png" `
            --remote 2>&1

        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓" -ForegroundColor Green
            $passCount++
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

Write-Host ""
Write-Host ("=" * 70)

if ($DryRun) {
    Write-Host "  DRY RUN complete — $($uploadList.Count) file(s) would be uploaded" -ForegroundColor Yellow
} elseif ($failCount -eq 0) {
    Write-Host "  ALL CLEAR: $passCount/$($uploadList.Count) uploaded successfully" -ForegroundColor Green
    Write-Host ""
    Write-Host "  CDN URLs:" -ForegroundColor White
    foreach ($item in $uploadList) {
        Write-Host "    $($item.CDNUrl)" -ForegroundColor Gray
    }
} else {
    Write-Host "  ATTENTION: $failCount failed, $passCount succeeded" -ForegroundColor Red
}

Write-Host ""
