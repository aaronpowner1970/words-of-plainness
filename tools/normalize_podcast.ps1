<#
.SYNOPSIS
    WoP Podcast Normalization — two-stage broadcast-level loudness correction.

.DESCRIPTION
    Fixes podcast recordings with uneven intra-file dynamics (loud/quiet
    variation within the same file) and normalizes to the WoP broadcast
    standard.

    Stage 1 — dynaudnorm: local dynamic range normalizer. Moves a gaussian
    window across the file and levels quiet and loud sections. Designed for
    voice recordings; more transparent than a traditional compressor for
    speech.

    Stage 2 — two-pass loudnorm (EBU R128): broadcast integrated-loudness
    target. Pass 1 measures the post-dynaudnorm signal. Pass 2 applies
    linear normalization to hit exact targets.

    Project standard (matches Ch 9 narration pipeline):
        Integrated loudness (I)     : -16 LUFS
        True peak max    (TP)       : -1.5 dBTP
        Loudness range   (LRA)      : 11 LU

    Output: VBR V2 MP3 via libmp3lame at 44.1 kHz, source channel layout
    preserved. Existing ID3 metadata is carried through.

    Requires ffmpeg and ffprobe on PATH.

.PARAMETER InputFile
    Absolute path to the source MP3 (or any ffmpeg-readable audio file).

.PARAMETER OutputFile
    Optional. Absolute path for the normalized output. Defaults to the input
    filename with "_normalized" suffix in the same folder.

.PARAMETER TargetI
    Integrated loudness target in LUFS. Default: -16.

.PARAMETER TargetTP
    True peak max in dBTP. Default: -1.5.

.PARAMETER TargetLRA
    Loudness range target in LU. Default: 11.

.PARAMETER SkipDynamic
    Skip the dynaudnorm stage; only apply two-pass loudnorm. Use when
    intra-file dynamics are already clean and only integrated loudness
    needs correction.

.PARAMETER KeepOriginal
    Do not overwrite if OutputFile exists. Default behavior overwrites.

.EXAMPLE
    # Default — full two-stage normalization
    .\tools\normalize_podcast.ps1 `
        -InputFile "C:\Users\aaron\Documents\working-folder\podcast-normalize\PO_04_01_Spiritual_Knowledge_original.mp3" `
        -OutputFile "C:\Users\aaron\Documents\working-folder\podcast-normalize\PO_04_01_Spiritual_Knowledge.mp3"

.EXAMPLE
    # Only loudnorm, skip dynamic range correction
    .\tools\normalize_podcast.ps1 `
        -InputFile "C:\path\to\podcast.mp3" `
        -SkipDynamic
#>

param(
    [Parameter(Mandatory)]
    [string]$InputFile,

    [string]$OutputFile = "",

    [double]$TargetI   = -16.0,
    [double]$TargetTP  = -1.5,
    [double]$TargetLRA = 11.0,

    [switch]$SkipDynamic,
    [switch]$KeepOriginal
)

$ErrorActionPreference = 'Stop'

# --- Preflight ---------------------------------------------------------------

if (-not (Test-Path -LiteralPath $InputFile)) {
    Write-Error "Input file not found: $InputFile"
    exit 1
}

if (-not (Get-Command ffmpeg  -ErrorAction SilentlyContinue)) {
    Write-Error "ffmpeg not found on PATH. Install from https://ffmpeg.org"
    exit 1
}
if (-not (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
    Write-Error "ffprobe not found on PATH. Install from https://ffmpeg.org"
    exit 1
}

$inputItem = Get-Item -LiteralPath $InputFile
if (-not $OutputFile) {
    $base = [System.IO.Path]::GetFileNameWithoutExtension($inputItem.Name)
    $OutputFile = Join-Path $inputItem.DirectoryName ("{0}_normalized.mp3" -f $base)
}

if ((Test-Path -LiteralPath $OutputFile) -and $KeepOriginal) {
    Write-Error "Output file already exists and -KeepOriginal was specified: $OutputFile"
    exit 1
}

# --- Source metadata ---------------------------------------------------------

function Get-AudioProbe {
    param([string]$Path)
    $json = & ffprobe -v error -print_format json -show_format -show_streams -select_streams a:0 -- $Path 2>&1 | Out-String
    return ($json | ConvertFrom-Json)
}

Write-Host ""
Write-Host "WoP Podcast Normalization" -ForegroundColor White
Write-Host ("=" * 70) -ForegroundColor DarkGray
Write-Host "Input  : $InputFile" -ForegroundColor Gray
Write-Host "Output : $OutputFile" -ForegroundColor Gray
Write-Host "Target : I=$TargetI LUFS, TP=$TargetTP dBTP, LRA=$TargetLRA LU" -ForegroundColor Gray
Write-Host "Stages : $(if ($SkipDynamic) { 'loudnorm only' } else { 'dynaudnorm -> two-pass loudnorm' })" -ForegroundColor Gray
Write-Host ""

$probe = Get-AudioProbe -Path $InputFile
$stream = $probe.streams[0]
$duration = [math]::Round([double]$probe.format.duration, 2)
$channels = $stream.channels
$sampleRate = $stream.sample_rate
$srcBitrate = if ($probe.format.bit_rate) { [int]([double]$probe.format.bit_rate / 1000) } else { '?' }

Write-Host "Source : ${duration}s, ${channels}ch, ${sampleRate}Hz, ${srcBitrate}kbps $($stream.codec_name)" -ForegroundColor DarkGray
Write-Host ""

# --- Stage 1 + Pass 1 analysis ----------------------------------------------
# Both stages are encoded in a single filter chain so pass 1 measures exactly
# what pass 2 will produce.

$dynPart = "dynaudnorm=f=500:g=31:p=0.71"

$pass1Filter = if ($SkipDynamic) {
    "loudnorm=I=${TargetI}:TP=${TargetTP}:LRA=${TargetLRA}:print_format=json"
} else {
    "${dynPart},loudnorm=I=${TargetI}:TP=${TargetTP}:LRA=${TargetLRA}:print_format=json"
}

Write-Host "Pass 1 — analyzing..." -ForegroundColor Cyan
$pass1Err = & ffmpeg -hide_banner -nostats -i $InputFile -af $pass1Filter -f null NUL 2>&1 | Out-String

# Extract the JSON block produced by loudnorm's print_format=json.
$jsonMatch = [regex]::Match($pass1Err, '(?s)\{[^{}]*"input_i"\s*:\s*"[^"]+"[^{}]*\}')
if (-not $jsonMatch.Success) {
    Write-Host $pass1Err -ForegroundColor Red
    Write-Error "Pass 1 loudnorm JSON not found in ffmpeg output."
    exit 1
}

$stats = $jsonMatch.Value | ConvertFrom-Json
$measuredI      = $stats.input_i
$measuredTP     = $stats.input_tp
$measuredLRA    = $stats.input_lra
$measuredThresh = $stats.input_thresh
$offset         = $stats.target_offset

Write-Host ("  Measured : I={0} LUFS   TP={1} dBTP   LRA={2} LU   thresh={3}" -f `
    $measuredI, $measuredTP, $measuredLRA, $measuredThresh) -ForegroundColor DarkGray
Write-Host ""

# --- Pass 2 — encode with linear loudnorm ------------------------------------

$loudnorm2 = "loudnorm=" +
    "I=${TargetI}:TP=${TargetTP}:LRA=${TargetLRA}:" +
    "measured_I=${measuredI}:measured_TP=${measuredTP}:" +
    "measured_LRA=${measuredLRA}:measured_thresh=${measuredThresh}:" +
    "offset=${offset}:linear=true:print_format=summary"

$pass2Filter = if ($SkipDynamic) { $loudnorm2 } else { "${dynPart},${loudnorm2}" }

Write-Host "Pass 2 — encoding..." -ForegroundColor Cyan

# VBR V2 via libmp3lame (~190 kbps average). 44.1 kHz fixed. Channel layout
# preserved from source. ID3 carried through with -map_metadata 0.
$pass2Err = & ffmpeg -hide_banner -nostats -y `
    -i $InputFile `
    -map_metadata 0 `
    -af $pass2Filter `
    -ar 44100 `
    -c:a libmp3lame -q:a 2 `
    $OutputFile 2>&1 | Out-String

if ($LASTEXITCODE -ne 0) {
    Write-Host $pass2Err -ForegroundColor Red
    Write-Error "Pass 2 encode failed."
    exit 1
}

# --- Verify output -----------------------------------------------------------

Write-Host "Verifying output..." -ForegroundColor Cyan
$outProbe = Get-AudioProbe -Path $OutputFile
$outDuration = [math]::Round([double]$outProbe.format.duration, 2)
$outBitrate  = [int]([double]$outProbe.format.bit_rate / 1000)
$outSize     = [math]::Round((Get-Item -LiteralPath $OutputFile).Length / 1MB, 2)

# Post-encode ebur128 measurement for a final sanity check.
$ebuErr = & ffmpeg -hide_banner -nostats -i $OutputFile -af "ebur128=peak=true" -f null NUL 2>&1 | Out-String
$iMatch   = [regex]::Match($ebuErr, '(?m)^\s*I:\s*(-?\d+\.\d+)\s*LUFS')
$tpMatch  = [regex]::Match($ebuErr, '(?m)^\s*Peak:\s*(-?\d+\.\d+)\s*dBFS')
$lraMatch = [regex]::Match($ebuErr, '(?m)^\s*LRA:\s*(-?\d+\.\d+)\s*LU')

$finalI   = if ($iMatch.Success)   { $iMatch.Groups[1].Value   } else { '?' }
$finalTP  = if ($tpMatch.Success)  { $tpMatch.Groups[1].Value  } else { '?' }
$finalLRA = if ($lraMatch.Success) { $lraMatch.Groups[1].Value } else { '?' }

Write-Host ""
Write-Host ("=" * 70) -ForegroundColor DarkGray
Write-Host "Output : $OutputFile" -ForegroundColor Green
Write-Host ("  ${outDuration}s, ${outBitrate}kbps VBR, ${outSize} MB") -ForegroundColor Gray
Write-Host ("  Final  : I={0} LUFS   Peak={1} dBFS   LRA={2} LU" -f $finalI, $finalTP, $finalLRA) -ForegroundColor Gray
Write-Host ("=" * 70) -ForegroundColor DarkGray
Write-Host ""
Write-Host "Done. Listen-check the output before uploading to R2." -ForegroundColor White
Write-Host ""
