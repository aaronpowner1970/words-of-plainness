# generate_youtube_videos.ps1
# Converts podcast overview MP3s + thumbnail PNGs into YouTube-ready MP4 videos.
# Requires ffmpeg on PATH (download from ffmpeg.org if needed).
#
# Staging folder structure:
#   YouTube Upload Staging Folder/
#   ├── audio/          ← 11 podcast overview MP3s from R2
#   ├── thumbnails/     ← 11 exported PNGs from thumbnail generator (1920x1080)
#   └── output/         ← ffmpeg creates 11 MP4s here
#
# Usage:
#   cd "C:\Users\aaron\Documents\working-folder\YouTube Upload Staging Folder"
#   C:\Users\aaron\Documents\words-of-plainness\tools\generate_youtube_videos.ps1

$stagingRoot = "C:\Users\aaron\Documents\working-folder\YouTube Upload Staging Folder"

$chapters = @(
    @{ num="01"; audio="PO_01_01_Introduction_to_Plainness.mp3"; thumb="thumb-ch01-introduction.png" }
    @{ num="02"; audio="PO_02_01_Our_Search.mp3"; thumb="thumb-ch02-our-search.png" }
    @{ num="03"; audio="PO_03_01_Academic_Knowledge.mp3"; thumb="thumb-ch03-academic-knowledge.png" }
    @{ num="04"; audio="PO_04_01_Spiritual_Knowledge.mp3"; thumb="thumb-ch04-spiritual-knowledge.png" }
    @{ num="05"; audio="PO_05_01_Sincere_Prayer.mp3"; thumb="thumb-ch05-sincere-prayer.png" }
    @{ num="06"; audio="PO_06_01_Embrace_the_Savior.mp3"; thumb="thumb-ch06-embrace-the-savior.png" }
    @{ num="07"; audio="PO_07_01_Prophecies_Birth_and_Youth.mp3"; thumb="thumb-ch07-prophecies-birth-youth.png" }
    @{ num="08"; audio="PO_08_01_Baptism_Temptations_Ministry.mp3"; thumb="thumb-ch08-baptism-temptations.png" }
    @{ num="09"; audio="PO_09_01_Yehoshua_the_Man.mp3"; thumb="thumb-ch09-yehoshua-the-man.png" }
    @{ num="10"; audio="PO_10_1_Suffering_Trial_Crucifixion_Resurrection.mp3"; thumb="thumb-ch10-suffering-trial.png" }
    @{ num="11"; audio="PO_11_01_The_Living_Christ.mp3"; thumb="thumb-ch11-the-living-christ.png" }
)

# Verify ffmpeg is available
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: ffmpeg not found on PATH. Download from https://ffmpeg.org" -ForegroundColor Red
    exit 1
}

# Verify staging folders exist
foreach ($dir in @("audio", "thumbnails", "output")) {
    $path = Join-Path $stagingRoot $dir
    if (-not (Test-Path $path)) {
        Write-Host "Creating $dir folder..." -ForegroundColor Yellow
        New-Item -ItemType Directory -Path $path | Out-Null
    }
}

$success = 0
$failed = 0

foreach ($ch in $chapters) {
    $audioPath = Join-Path $stagingRoot "audio\$($ch.audio)"
    $thumbPath = Join-Path $stagingRoot "thumbnails\$($ch.thumb)"
    $outputPath = Join-Path $stagingRoot "output\WoP_Ch$($ch.num)_PodcastOverview.mp4"

    # Check inputs exist
    if (-not (Test-Path $audioPath)) {
        Write-Host "  SKIP Ch $($ch.num): audio file not found: $($ch.audio)" -ForegroundColor Red
        $failed++
        continue
    }
    if (-not (Test-Path $thumbPath)) {
        Write-Host "  SKIP Ch $($ch.num): thumbnail not found: $($ch.thumb)" -ForegroundColor Red
        $failed++
        continue
    }

    Write-Host "Processing Chapter $($ch.num)..." -ForegroundColor Cyan

    ffmpeg -loop 1 -i $thumbPath -i $audioPath -c:v libx264 -tune stillimage -c:a aac -b:a 192k -pix_fmt yuv420p -shortest -y $outputPath 2>$null

    if ($LASTEXITCODE -eq 0) {
        $size = [math]::Round((Get-Item $outputPath).Length / 1MB, 1)
        Write-Host "  Done: WoP_Ch$($ch.num)_PodcastOverview.mp4 ($size MB)" -ForegroundColor Green
        $success++
    } else {
        Write-Host "  FAILED: Chapter $($ch.num) — check ffmpeg output" -ForegroundColor Red
        $failed++
    }
}

Write-Host ""
Write-Host "Complete: $success succeeded, $failed failed" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Yellow" })
Write-Host "Output folder: $stagingRoot\output\" -ForegroundColor Cyan
